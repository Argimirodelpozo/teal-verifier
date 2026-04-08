"""
AVMTranspiler — TEAL-to-C++ transpiler using tree-sitter-teal grammar.

Parses TEAL programs into AST nodes via tree-sitter, then generates C++ code
that models AVM execution using the structures in cbmc_avm.h and
cbmc_opcodes.h.
"""

import base64
import re
import sys
from pathlib import Path

import tree_sitter
import tree_sitter_teal


# ---------------------------------------------------------------------------
# Tree-sitter setup
# ---------------------------------------------------------------------------

_LANG = tree_sitter.Language(tree_sitter_teal.language())
_PARSER = tree_sitter.Parser(_LANG)


# ---------------------------------------------------------------------------
# Named-constant tables (for `int NoOp`, `int pay`, etc.)
# ---------------------------------------------------------------------------

NAMED_INT_CONSTANTS = {
    # OnCompletion values
    "NoOp": 0, "OptIn": 1, "CloseOut": 2,
    "ClearState": 3, "UpdateApplication": 4, "DeleteApplication": 5,
    # TxnType values
    "pay": 1, "keyreg": 2, "acfg": 3, "axfer": 4,
    "afrz": 5, "appl": 6, "hb": 7, "stpf": 8,
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def process_label(label: str, prefix: str = "") -> str:
    """Convert TEAL label symbols to C++-safe labels."""
    safe = (label
            .replace(".", "_dot_")
            .replace("-", "_dash_")
            .replace("@", "_at_")
            .replace("[", "_lb_")
            .replace("]", "_rb_"))
    return prefix + "L_" + safe


def parse_hex_literal_as_init_list(hex_number: str) -> str:
    """Convert hex/base64/string literal to C++ initializer list."""
    if hex_number == "" or hex_number == "0x":
        return "{}"

    if hex_number.startswith("base64("):
        hex_number = hex_number.replace("base64(", "").replace(")", "")
        raw = bytearray(base64.b64decode(hex_number))
    elif hex_number.startswith("b32("):
        hex_number = hex_number.replace("b32(", "").replace(")", "")
        raw = bytearray(base64.b32decode(hex_number))
    elif hex_number.startswith('"') and hex_number.endswith('"'):
        raw = bytearray(hex_number[1:-1].encode("ascii"))
    elif hex_number.startswith("0x"):
        hex_str = hex_number[2:]
        if len(hex_str) == 0:
            return "{}"
        raw = bytearray.fromhex(hex_str)
    else:
        # Assume string literal without quotes (shouldn't happen with tree-sitter)
        raw = bytearray(hex_number.encode("ascii"))

    if len(raw) == 0:
        return "{}"

    return "{" + ",".join(str(b) for b in raw) + "}"


def generate_retsub_dispatch(callsub_total: int, prefix: str = "") -> str:
    """Generate the single retsub dispatch block emitted at end of transpiled code."""
    out = f"{prefix}_retsub_dispatch:\n"
    out += "\tretsub_cleanup(s, ctx);\n"
    out += "\t{\n"
    out += "\t\tint _ret = _csub[--_csub_sp];\n"
    out += "\t\tswitch (_ret){\n"
    for i in range(callsub_total):
        out += f"\t\t\tcase {i}:\n"
        out += f"\t\t\tgoto {prefix}callsub_{i};\n"
    out += "\t\t}\n"
    out += "\t}\n"
    return out


def generate_match_branches(labels: list[str], prefix: str = "") -> str:
    """Generate branching logic for the `match` opcode.

    Stack before: ... x_0 x_1 ... x_{n-1} target
    match label_0 label_1 ... label_{n-1}
    Compare target (top) against x_i. If target == x_i, branch to label_i.
    s.get(0) = target, s.get(n) = x_0, s.get(n-1) = x_1, ..., s.get(1) = x_{n-1}.
    """
    n = len(labels)
    out = "\t"
    for i in range(n):
        safe = process_label(labels[i], prefix)
        # x_i is at s.get(n - i)
        depth = n - i
        out += f"if (_sv_eq(s.get(0), s.get({depth}))){{ s.discard({n + 1}); goto {safe};}}\n"
        out += "\telse "
    out += f"s.discard({n + 1});\n"
    return out


def generate_switch_branches(labels: list[str], prefix: str = "") -> str:
    """Generate branching logic for the `switch` opcode."""
    out = "\t{\n"
    out += "\t\tuint64_t _sw = s.pop().value;\n"
    for i, lab in enumerate(labels):
        safe = process_label(lab, prefix)
        out += f"\t\tif (_sw == {i}) goto {safe};\n"
    out += "\t}\n"
    return out


# ---------------------------------------------------------------------------
# Preprocessing: handle grammar gaps
# ---------------------------------------------------------------------------

_OPCODE_KEYWORDS = {
    "swap", "pop", "dup", "dup2", "return", "assert", "err",
    "select", "log", "int", "byte", "len", "concat",
    "balance", "min_balance", "args",
}


def _normalize_teal_int(s: str) -> str:
    """Normalize a TEAL integer literal: strip underscores (1_000_000 → 1000000)."""
    return s.replace("_", "")


def _parse_bytecblock_args(raw: str) -> list[str]:
    """Parse bytecblock arguments handling mixed quoted strings and hex values.

    tree-sitter-teal's string_argument rule is greedy and merges all content
    between the first and last quote into a single node.  We parse manually
    and convert quoted strings to hex so tree-sitter only sees hex arguments.
    """
    args: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] in (" ", "\t"):
            i += 1
            continue
        if raw[i] == '"':
            # Quoted string: find matching close quote
            j = raw.index('"', i + 1)
            text = raw[i + 1 : j]
            hex_str = "0x" + text.encode("ascii").hex()
            args.append(hex_str if hex_str != "0x" else "0x00")
            i = j + 1
        else:
            # Unquoted token (hex literal, TMPL_*, etc.)
            j = i
            while j < len(raw) and raw[j] not in (" ", "\t"):
                j += 1
            token = raw[i:j]
            if token.startswith("TMPL_"):
                args.append("0x00")
            else:
                args.append(token)
            i = j
    return args


def _preprocess_teal(source: str) -> str:
    """
    Preprocess TEAL source to work around tree-sitter-teal grammar limitations:
    - `int <name>` (named constants like NoOp, pay) → `pushint <value>`
    - `byte 0x...` / `byte "..."` / `byte base64(...)` → `pushbytes ...`
    - `addr <base32>` → `pushbytes <decoded>`
    - labels whose name collides with opcodes (e.g. `swap:`) → renamed
    - references to those labels (e.g. `bnz swap`) → updated too
    - underscore-separated integers (1_000_000) → normalized (1000000)
    - TMPL_* template variables → placeholder values (0 for int, 0x00 for bytes)
    """
    lines = source.split("\n")

    # First pass: find labels that collide with opcode keywords
    label_renames: dict[str, str] = {}
    for line in lines:
        stripped = line.split("//")[0].split(";")[0].strip()
        if stripped.endswith(":") and not stripped.startswith("#"):
            label_name = stripped[:-1].strip()
            if label_name in _OPCODE_KEYWORDS:
                label_renames[label_name] = f"_label_{label_name}"

    result = []
    for line in lines:
        stripped = line.split("//")[0].split(";")[0].strip()
        if not stripped:
            result.append(line)
            continue

        # Strip #pragma typetrack (tree-sitter-teal parses this as ERROR node)
        if stripped.startswith("#pragma typetrack"):
            continue

        parts = stripped.split()
        opcode = parts[0] if parts else ""

        # switch/match: always strip '*' from labels, apply renames
        if opcode in ("switch", "match") and len(parts) > 1:
            raw_labels = [l.lstrip("*") for l in parts[1:]]
            new_labels = [label_renames.get(l, l) for l in raw_labels]
            result.append(f"{opcode} {' '.join(new_labels)}")
            continue

        # Branch instructions: strip '*' from label references, apply renames
        if opcode in ("b", "bz", "bnz", "callsub") and len(parts) == 2:
            ref = parts[1].lstrip("*")
            if ref in label_renames:
                ref = label_renames[ref]
            result.append(f"{opcode} {ref}")
            continue

        # Label definitions: strip '*' prefix, apply renames
        if stripped.endswith(":") and not stripped.startswith("#"):
            label_name = stripped[:-1].strip().lstrip("*")
            if label_name in label_renames:
                result.append(f"{label_renames[label_name]}:")
            else:
                result.append(f"{label_name}:")
            continue

        # intcblock: normalize underscored ints, replace TMPL_* with 0
        if opcode == "intcblock" and len(parts) > 1:
            normalized = ["intcblock"]
            for arg in parts[1:]:
                if arg.startswith("TMPL_"):
                    normalized.append("0")  # placeholder for template variable
                else:
                    normalized.append(_normalize_teal_int(arg))
            result.append(" ".join(normalized))
            continue

        # bytecblock: parse mixed string/hex args and convert all to hex
        # (tree-sitter-teal merges quoted strings separated by hex into one blob)
        if opcode == "bytecblock":
            raw_args = stripped[len("bytecblock"):].strip()
            if raw_args:
                hex_args = _parse_bytecblock_args(raw_args)
                result.append("bytecblock " + " ".join(hex_args))
            else:
                result.append(stripped)
            continue

        # pushint / int with underscore-separated numbers
        if opcode in ("pushint", "int") and len(parts) == 2:
            arg = parts[1]
            if arg.startswith("TMPL_"):
                result.append("pushint 0")  # placeholder
                continue
            # Normalize underscored ints
            arg = _normalize_teal_int(arg)
            if opcode == "int":
                if arg in NAMED_INT_CONSTANTS:
                    result.append(f"pushint {NAMED_INT_CONSTANTS[arg]}")
                    continue
                if arg.startswith("0x") or arg.startswith("0X"):
                    result.append(f"pushint {int(arg, 16)}")
                    continue
            result.append(f"{opcode} {arg}")
            continue

        # byte <literal> → pushbytes <literal>
        if opcode == "byte" and len(parts) >= 2:
            rest = stripped[len("byte "):].strip()
            if rest == '""':
                result.append("pushbytes 0x")
            else:
                result.append(f"pushbytes {rest}")
            continue

        # pushbytes "": empty string literal (tree-sitter can't parse it)
        if opcode == "pushbytes" and stripped == 'pushbytes ""':
            result.append("pushbytes 0x")
            continue

        # pushbytes "string": convert quoted strings to hex for consistency
        if opcode == "pushbytes" and len(parts) >= 2:
            rest = stripped[len("pushbytes "):].strip()
            if rest.startswith('"') and rest.endswith('"'):
                text = rest[1:-1]
                hex_str = "0x" + text.encode("ascii").hex()
                result.append(f"pushbytes {hex_str}" if hex_str != "0x" else "pushbytes 0x")
                continue

        # addr <base32_address> → pushbytes with decoded 32-byte public key
        if opcode == "addr" and len(parts) == 2:
            try:
                import base64
                # Algorand addresses are base32-encoded (no padding): 32-byte pk + 4-byte checksum
                addr_str = parts[1]
                # Add padding if needed
                padded = addr_str + "=" * ((8 - len(addr_str) % 8) % 8)
                decoded = base64.b32decode(padded)
                pk_bytes = decoded[:32]  # first 32 bytes are the public key
                hex_str = "0x" + pk_bytes.hex().upper()
                result.append(f"pushbytes {hex_str}")
            except Exception:
                result.append("pushbytes 0x00")  # fallback placeholder
            continue

        # gload T S → group scratch read (nondeterministic, pops nothing, pushes 1)
        if opcode == "gload" and len(parts) == 3:
            result.append(f"//RAW_CPP:\tgload_op(s, {parts[1]}, {parts[2]});")
            continue
        # gloads S → group scratch read (nondeterministic, pops txn index, pushes 1)
        if opcode == "gloads" and len(parts) == 2:
            result.append(f"//RAW_CPP:\tgloads_op(s, {parts[1]});")
            continue
        # gaid T → group app ID (nondeterministic, pops nothing, pushes 1)
        if opcode == "gaid" and len(parts) == 2:
            result.append(f"//RAW_CPP:\tgaid_op(s, {parts[1]});")
            continue
        # gaids → group app ID from stack (nondeterministic, pops txn index, pushes 1)
        if opcode == "gaids":
            result.append("//RAW_CPP:\tgaids_op(s);")
            continue

        # vrf_verify standard → nondeterministic VRF stub
        if opcode == "vrf_verify" and len(parts) == 2:
            result.append("//RAW_CPP:\tvrf_verify(s, 0);")
            continue
        # block BlkSeed/BlkTimestamp → nondeterministic block field
        if opcode == "block" and len(parts) == 2:
            field_map = {"BlkSeed": "BlkSeed", "BlkTimestamp": "BlkTimestamp"}
            field = field_map.get(parts[1], "BlkTimestamp")
            result.append(f"//RAW_CPP:\tblock_field(s, {field});")
            continue
        # base64_decode URLEncoding/StdEncoding → nondeterministic decode
        if opcode == "base64_decode" and len(parts) == 2:
            result.append("//RAW_CPP:\tbase64_decode(s, 0);")
            continue
        # EC ops: ec_add, ec_scalar_mul, etc. with curve group argument
        if opcode in ("ec_add", "ec_scalar_mul", "ec_multi_scalar_mul",
                       "ec_subgroup_check", "ec_map_to", "ec_pairing_check") and len(parts) == 2:
            group_map = {"BN254g1": "BN254g1", "BN254g2": "BN254g2",
                         "BLS12_381g1": "BLS12_381g1", "BLS12_381g2": "BLS12_381g2"}
            group = group_map.get(parts[1], "BN254g1")
            result.append(f"//RAW_CPP:\t{opcode}(s, {group});")
            continue

        result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# AST → C++ transpilation
# ---------------------------------------------------------------------------

class TEALTranspiler:
    """Transpiles a TEAL program (via tree-sitter AST) to C++ code."""

    # State ops that consume a key from the stack (pushed by preceding bytec/pushbytes)
    _GLOBAL_STATE_OPS = {"app_global_get", "app_global_put", "app_global_del",
                         "app_global_get_ex"}
    _LOCAL_STATE_OPS = {"app_local_get", "app_local_put", "app_local_del",
                        "app_local_get_ex"}

    def __init__(self, label_prefix: str = ""):
        self.callsub_n = 0
        self.callsub_total = 0
        self.output = ""
        self._emitted_labels: set[str] = set()
        self._intcblock: list[int] | None = None
        self._bytecblock: list[str] | None = None  # C++ initializer strings
        # Direct-index state: key init_list → assigned index
        self._global_key_map: dict[str, int] = {}  # init_list → global slot index
        self._local_key_map: dict[str, int] = {}   # init_list → local key index
        # Pending key: (init_list, byte_count) waiting to be consumed by a state op
        self._pending_key: tuple[str, int] | None = None
        self._label_prefix = label_prefix

    def _label(self, label: str) -> str:
        """Convert TEAL label to C++-safe label with per-contract prefix."""
        return process_label(label, self._label_prefix)

    def _emit(self, code: str):
        self.output += code

    def _emit_op(self, code: str):
        """Emit an opcode line, appending AVM_BAIL_ON_PANIC() for early exit on panic."""
        self.output += code
        self.output += "\tAVM_BAIL_ON_PANIC();\n"

    @staticmethod
    def _unroll_dupn(n: int) -> str:
        """Unroll dupn into n inline pushes (n known at transpile time)."""
        lines = ["\tavm_assert_check(s.currentSize > 0);\n"]
        lines.append("\t{ StackValue _v = s.stack[s.currentSize - 1];\n")
        for _ in range(n):
            lines.append("\t  s.stack[s.currentSize++] = _v;\n")
        lines.append("\t}\n")
        return "".join(lines)

    @staticmethod
    def _unroll_cover(depth: int) -> str:
        """Unroll cover into inline assignments (depth known at transpile time)."""
        lines = [f"\tavm_assert_check(s.currentSize > {depth});\n"]
        lines.append("\t{ StackValue _top = s.stack[s.currentSize - 1];\n")
        for i in range(depth):
            lines.append(f"\t  s.stack[s.currentSize - 1 - {i}] = s.stack[s.currentSize - 2 - {i}];\n")
        lines.append(f"\t  s.stack[s.currentSize - 1 - {depth}] = _top;\n")
        lines.append("\t}\n")
        return "".join(lines)

    @staticmethod
    def _unroll_uncover(depth: int) -> str:
        """Unroll uncover into inline assignments (depth known at transpile time)."""
        lines = [f"\tavm_assert_check(s.currentSize > {depth});\n"]
        lines.append(f"\t{{ StackValue _val = s.stack[s.currentSize - 1 - {depth}];\n")
        for i in range(depth, 0, -1):
            lines.append(f"\t  s.stack[s.currentSize - 1 - {i}] = s.stack[s.currentSize - {i}];\n")
        lines.append("\t  s.stack[s.currentSize - 1] = _val;\n")
        lines.append("\t}\n")
        return "".join(lines)

    def _emit_inline_pushbytes(self, init: str):
        """Emit inline pushbytes: zero-init local + direct byte assignment.

        Avoids sv_bytes() constructor and _cbmc_bytecopy loop.
        Uses local StackValue _z = {} for zero-init (tail bytes = 0),
        then assigns specific bytes loop-free for CBMC.
        """
        if init == "{}":
            self._emit(
                "\t{ __CPROVER_assume(s.currentSize < CBMC_STACK_MAX);\n"
                "\t  StackValue _z = {}; _z._is_bytes = true;\n"
                "\t  s.stack[s.currentSize++] = _z; }\n"
            )
            return
        byte_strs = init.strip("{}").split(",")
        n = len(byte_strs)
        lines = ["\t{ __CPROVER_assume(s.currentSize < CBMC_STACK_MAX);"]
        lines.append(f"\t  StackValue _z = {{}}; _z._is_bytes = true; _z.byteslice_len = {n};")
        for i, bv in enumerate(byte_strs):
            lines.append(f"\t  _z.byteslice[{i}] = {bv.strip()};")
        lines.append("\t  s.stack[s.currentSize++] = _z; }")
        self._emit("\n".join(lines) + "\n")

    # -- child-node helpers -------------------------------------------------

    @staticmethod
    def _child_text(node, child_type: str) -> str | None:
        """Get the text of the first child with given type."""
        for ch in node.children:
            if ch.type == child_type:
                return ch.text.decode()
        return None

    @staticmethod
    def _children_text(node, child_type: str) -> list[str]:
        """Get texts of all children with given type."""
        return [ch.text.decode() for ch in node.children if ch.type == child_type]

    @staticmethod
    def _opcode_text(node) -> str:
        """Get the opcode keyword text (first child)."""
        return node.children[0].text.decode() if node.children else ""

    def _numeric_arg(self, node) -> int:
        """Extract numeric argument, handling tree-sitter's negative number gap.

        tree-sitter-teal can't tokenize '-1' as a single numeric_argument.
        Instead it produces: ERROR('-') + numeric_argument('1').
        We detect the ERROR('-') child and negate the value.
        """
        has_minus = any(
            ch.type == "ERROR" and ch.text.decode().strip() == "-"
            for ch in node.children
        )
        raw = self._child_text(node, "numeric_argument")
        if raw is None:
            return 0
        val = int(raw)
        return -val if has_minus else val

    def _numeric_args(self, node) -> list[int]:
        """Extract all numeric arguments."""
        texts = self._children_text(node, "numeric_argument")
        return [int(raw) for raw in texts]

    def _bytes_arg(self, node) -> str:
        """Extract a bytes argument (hex or string) as C++ initializer."""
        hex_arg = self._child_text(node, "hexbytes_argument")
        if hex_arg is not None:
            return parse_hex_literal_as_init_list(hex_arg)
        str_arg = self._child_text(node, "string_argument")
        if str_arg is not None:
            return parse_hex_literal_as_init_list(str_arg)
        base64_arg = self._child_text(node, "base64_argument")
        if base64_arg is not None:
            return parse_hex_literal_as_init_list(f"base64({base64_arg})")
        return "{}"

    def _bytes_args(self, node) -> list[str]:
        """Extract all bytes arguments as C++ initializers."""
        result = []
        for ch in node.children:
            if ch.type == "hexbytes_argument":
                result.append(parse_hex_literal_as_init_list(ch.text.decode()))
            elif ch.type == "string_argument":
                result.append(parse_hex_literal_as_init_list(ch.text.decode()))
            elif ch.type == "base64_argument":
                result.append(parse_hex_literal_as_init_list(f"base64({ch.text.decode()})"))
        return result

    def _label_arg(self, node) -> str:
        """Extract a label_identifier child."""
        return self._child_text(node, "label_identifier") or ""

    def _label_args(self, node) -> list[str]:
        """Extract all label_identifier children."""
        return self._children_text(node, "label_identifier")

    def _field_name(self, node) -> str:
        """Extract the field name (for txn/global opcodes — the non-keyword child)."""
        for ch in node.children:
            # Field names are named nodes like ApplicationID, Sender, etc.
            if ch.type not in ("txn", "txna", "gtxn", "gtxna", "gtxns", "gtxnsa",
                               "txnas", "gtxnas", "gtxnsas",
                               "itxn", "itxna", "gitxn", "gitxna",
                               "itxnas", "gitxnas",
                               "global", "itxn_field", "json_ref",
                               "acct_params_get", "app_params_get",
                               "asset_holding_get", "asset_params_get",
                               "numeric_argument", "label_identifier",
                               "hexbytes_argument", "string_argument"):
                return ch.text.decode()
        return ""

    # -- count callsub for retsub dispatch ----------------------------------

    def _count_callsubs(self, root):
        """Count total callsub opcodes for retsub switch generation."""
        count = 0
        for child in root.children:
            if child.type == "callsub_opcode":
                count += 1
        return count

    # -- direct-index key collection ----------------------------------------

    def _resolve_bytec_init(self, op_text: str, node=None) -> str | None:
        """Resolve a bytec/pushbytes opcode to its C++ initializer string.

        Returns the init_list (e.g. '{115,116,97,116,117,115}') or None if
        the key can't be statically determined.
        """
        if self._bytecblock is None:
            return None
        # bytec_N shorthand
        if op_text.startswith("bytec_"):
            idx = int(op_text.split("_")[1])
            if idx < len(self._bytecblock):
                return self._bytecblock[idx]
        # bytec N (single numeric arg)
        if op_text == "bytec" and node is not None:
            n = self._numeric_arg(node)
            if n < len(self._bytecblock):
                return self._bytecblock[n]
        return None

    @staticmethod
    def _init_list_byte_count(init: str) -> int:
        """Count bytes in a C++ initializer like '{0x73,0x74,...}'."""
        if init == "{}":
            return 0
        return len(init.strip("{}").split(","))

    @staticmethod
    def _init_list_to_bytes(init: str) -> list[int]:
        """Convert '{99,111,117,...}' to list of ints."""
        if init == "{}":
            return []
        return [int(b.strip()) for b in init.strip("{}").split(",")]

    @staticmethod
    def _init_list_to_c_array(init: str) -> str:
        """Convert '{0x73,0x74}' to a C array literal '(const uint8_t[]){0x73,0x74}'."""
        return f"(const uint8_t[]){init}"

    def _collect_static_keys(self, root):
        """First pass: scan bytecblock + state ops to assign sequential indices.

        Walks the AST children looking for patterns:
          bytec_N / bytec N / pushbytes <literal> → app_global_get/put/del/get_ex
          bytec_N / bytec N / pushbytes <literal> → app_local_get/put/del/get_ex
        and assigns each unique key a sequential array index (0, 1, 2, ...).
        """
        # First, find bytecblock to resolve bytec references
        bytecblock = None
        for child in root.children:
            if child.type == "bytecblock_opcode":
                args = self._bytes_args(child)
                bytecblock = args
                break

        children = root.children
        n = len(children)
        for i in range(n - 1):
            child = children[i]
            op_text = child.text.decode().split("//")[0].strip()
            parts = op_text.split()
            opcode = parts[0] if parts else ""

            # Determine the init_list for this instruction
            init = None
            if child.type == "pushbytes_opcode":
                init = self._bytes_arg(child)
            elif child.type == "zero_argument_opcode" and opcode.startswith("bytec_"):
                if bytecblock is not None:
                    idx = int(opcode.split("_")[1])
                    if idx < len(bytecblock):
                        init = bytecblock[idx]
            elif child.type == "single_numeric_argument_opcode" and opcode == "bytec":
                if bytecblock is not None:
                    n_arg = self._numeric_arg(child)
                    if n_arg < len(bytecblock):
                        init = bytecblock[n_arg]

            if init is None:
                continue

            # Look ahead for a state op (skip comments)
            for j in range(i + 1, min(i + 3, n)):
                nxt = children[j]
                if nxt.type == "comment":
                    continue
                nxt_op = nxt.text.decode().split("//")[0].strip().split()[0] if nxt.text else ""
                if nxt_op in self._GLOBAL_STATE_OPS:
                    if init not in self._global_key_map:
                        self._global_key_map[init] = len(self._global_key_map)
                elif nxt_op in self._LOCAL_STATE_OPS:
                    if init not in self._local_key_map:
                        self._local_key_map[init] = len(self._local_key_map)
                break  # only check the first non-comment sibling

    def _flush_pending_key(self):
        """Emit a deferred pushbytes that wasn't consumed by a state op."""
        if self._pending_key is not None:
            init, _ = self._pending_key
            self._pending_key = None
            self._emit_inline_pushbytes(init)

    def _emit_fused_global_op(self, op: str, init: str, nbytes: int):
        """Emit fused global state op: O(1) direct array access by compile-time index.

        No scanning, no hashing at runtime. The key index is assigned during
        the first pass (_collect_static_keys) and the transpiler emits direct
        gs_get_idx/gs_put_idx/gs_del_idx calls.
        """
        idx = self._global_key_map[init]
        c_arr = self._init_list_to_c_array(init)
        if op == "app_global_get":
            self._emit(
                f"\t{{ StackValue* _gv = gs_get_idx(BS.globals, {idx});\n"
                f"\t  if (_gv) stack_push(s, *_gv); else pushint(s, 0); }}\n"
            )
        elif op == "app_global_put":
            self._emit(
                f"\t{{ StackValue _val = stack_pop(s);\n"
                f"\t  gs_put_idx(BS.globals, {idx}, {c_arr}, {nbytes}, _val); }}\n"
            )
            self._emit("\tAVM_BAIL_ON_PANIC();\n")
        elif op == "app_global_del":
            self._emit(f"\tgs_del_idx(BS.globals, {idx});\n")
        elif op == "app_global_get_ex":
            self._emit(
                f"\t{{ stack_pop(s); // app_id (ignored, current app only)\n"
                f"\t  StackValue* _gv = gs_get_idx(BS.globals, {idx});\n"
                f"\t  if (_gv) {{ stack_push(s, *_gv); pushint(s, 1); }}\n"
                f"\t  else {{ pushint(s, 0); pushint(s, 0); }} }}\n"
            )

    def _emit_fused_local_op(self, op: str, init: str, nbytes: int):
        """Emit fused local state op: O(1) direct array access by compile-time index."""
        idx = self._local_key_map[init]
        c_arr = self._init_list_to_c_array(init)
        if op == "app_local_get":
            self._emit(
                f"\t{{ StackValue _acct = stack_pop(s);\n"
                f"\t  const uint8_t* _addr = _resolve_account_addr(_acct, TxnGroup[currentTxn]);\n"
                f"\t  StackValue* _lv = ls_get_idx(BS.locals, _addr, {idx});\n"
                f"\t  if (_lv) stack_push(s, *_lv); else pushint(s, 0); }}\n"
            )
        elif op == "app_local_put":
            self._emit(
                f"\t{{ StackValue _val = stack_pop(s);\n"
                f"\t  StackValue _acct = stack_pop(s);\n"
                f"\t  const uint8_t* _addr = _resolve_account_addr(_acct, TxnGroup[currentTxn]);\n"
                f"\t  LocalEntry* _le = ls_find_account(BS.locals, _addr);\n"
                f"\t  avm_assert_check(_le != 0);\n"
                f"\t  ls_put_idx(BS.locals, _addr, {idx}, {c_arr}, {nbytes}, _val); }}\n"
            )
            self._emit("\tAVM_BAIL_ON_PANIC();\n")
        elif op == "app_local_del":
            self._emit(
                f"\t{{ StackValue _acct = stack_pop(s);\n"
                f"\t  const uint8_t* _addr = _resolve_account_addr(_acct, TxnGroup[currentTxn]);\n"
                f"\t  LocalEntry* _le = ls_find_account(BS.locals, _addr);\n"
                f"\t  avm_assert_check(_le != 0);\n"
                f"\t  ls_del_idx(BS.locals, _addr, {idx}); }}\n"
            )
            self._emit("\tAVM_BAIL_ON_PANIC();\n")
        elif op == "app_local_get_ex":
            self._emit(
                f"\t{{ StackValue _app_id = stack_pop(s);\n"
                f"\t  StackValue _acct = stack_pop(s);\n"
                f"\t  const uint8_t* _addr = _resolve_account_addr(_acct, TxnGroup[currentTxn]);\n"
                f"\t  LocalEntry* _le = ls_find_account(BS.locals, _addr);\n"
                f"\t  if (!_le) {{ pushint(s, 0); pushint(s, 0); }}\n"
                f"\t  else {{ StackValue* _lv = ls_get_idx(BS.locals, _addr, {idx});\n"
                f"\t    if (_lv) {{ stack_push(s, *_lv); pushint(s, 1); }}\n"
                f"\t    else {{ pushint(s, 0); pushint(s, 0); }} }} }}\n"
            )

    # -- node visitors ------------------------------------------------------

    def visit(self, node):
        """Dispatch to the appropriate visitor for a node type."""
        handler = getattr(self, f"_visit_{node.type}", None)
        if handler:
            handler(node)
        else:
            # For ERROR nodes, try to recover
            if node.type == "ERROR":
                self._flush_pending_key()
                self._visit_error(node)
            # Silently skip unknown node types (comments, whitespace, etc.)

    def _visit_source(self, node):
        for child in node.children:
            # Flush pending key before any node that can't consume it.
            # Only zero_argument_opcode (state ops) and comments are exempt.
            if (self._pending_key is not None
                    and child.type != "comment"
                    and child.type != "zero_argument_opcode"):
                self._flush_pending_key()
            self.visit(child)

    def _visit_pragma(self, node):
        # Ignore pragma directives (version info)
        pass

    def _visit_comment(self, node):
        # RAW_CPP: comments are preprocessor-injected C++ code
        text = node.text.decode()
        if text.startswith("//RAW_CPP:"):
            raw = text[len("//RAW_CPP:"):]
            self._emit_op(raw + "\n")

    def _visit_label(self, node):
        label = self._label_arg(node)
        safe = self._label(label)
        if safe in self._emitted_labels:
            return  # skip duplicate label
        self._emitted_labels.add(safe)
        self._emit(f"{safe}: ;\n")

    _ZERO_ARG_MAP = {
        # Arithmetic
        "+": "\tadd(s);\n",
        "-": "\tsub(s);\n",
        "*": "\tmul(s);\n",
        "/": "\tdiv_op(s);\n",
        "%": "\tmod_op(s);\n",
        # Comparisons
        "==": "\tbool_eq(s);\n",
        "!=": "\tbool_neq(s);\n",
        "<": "\tbool_lt(s);\n",
        ">": "\tbool_gt(s);\n",
        "<=": "\tbool_leq(s);\n",
        ">=": "\tbool_geq(s);\n",
        # Boolean logic
        "&&": "\tbool_and(s);\n",
        "||": "\tbool_or(s);\n",
        "!": "\tnot_logical(s);\n",
        # Bitwise
        "~": "\tbitwise_neg(s);\n",
        "&": "\tbitwise_and(s);\n",
        "|": "\tbitwise_or(s);\n",
        "^": "\tbitwise_xor(s);\n",
        "shr": "\tbitwise_shr(s);\n",
        "shl": "\tbitwise_shl(s);\n",
        # Stack
        "dup": "\tdup(s);\n",
        "dup2": "\tdup2(s);\n",
        "pop": "\tpop(s);\n",
        "swap": "\tswap(s);\n",
        "select": "\tselect(s);\n",
        "assert": "\tavm_assert(s);\n",
        # Byte ops
        "concat": "\tconcat(s);\n",
        "len": "\tlen(s);\n",
        "itob": "\titob(s);\n",
        "btoi": "\tbtoi(s);\n",
        "bzero": "\tbzero(s);\n",
        "substring3": "\tsubstring3(s);\n",
        "extract3": "\textract3(s);\n",
        "getbyte": "\tgetbyte(s);\n",
        "setbyte": "\tsetbyte(s);\n",
        "getbit": "\tgetbit(s);\n",
        "setbit": "\tsetbit(s);\n",
        "bitlen": "\tbitlen(s);\n",
        "replace3": "\treplace3(s);\n",
        "extract_uint16": "\textract_uint16(s);\n",
        "extract_uint32": "\textract_uint32(s);\n",
        "extract_uint64": "\textract_uint64(s);\n",
        # Wide math
        "mulw": "\tmulw(s);\n",
        "addw": "\taddw(s);\n",
        "divw": "\tdivw(s);\n",
        "divmodw": "\tdivmodw(s);\n",
        "exp": "\texp_op(s);\n",
        "expw": "\texpw(s);\n",
        "sqrt": "\tsqrt_op(s);\n",
        # Crypto
        "sha256": "\tsha256(s);\n",
        "sha512_256": "\tsha512_256(s);\n",
        "sha3_256": "\tsha3_256(s);\n",
        "keccak256": "\tkeccak256(s);\n",
        "ed25519verify": "\ted25519verify(s);\n",
        "ed25519verify_bare": "\ted25519verify_bare(s);\n",
        # Logging
        "log": "\tavm_log(s, ctx);\n",
        # State ops
        "app_global_put": "\tapp_global_put(s, BS, ctx);\n",
        "app_global_get": "\tapp_global_get(s, BS, ctx);\n",
        "app_global_get_ex": "\tapp_global_get_ex(s, BS, ctx);\n",
        "app_global_del": "\tapp_global_del(s, BS, ctx);\n",
        "app_local_put": "\tapp_local_put(s, BS, TxnGroup[currentTxn], ctx);\n",
        "app_local_get": "\tapp_local_get(s, BS, TxnGroup[currentTxn], ctx);\n",
        "app_local_get_ex": "\tapp_local_get_ex(s, BS, TxnGroup[currentTxn], ctx);\n",
        "app_local_del": "\tapp_local_del(s, BS, TxnGroup[currentTxn], ctx);\n",
        "app_opted_in": "\tapp_opted_in(s, BS, TxnGroup[currentTxn], ctx);\n",
        # Box ops
        "box_create": "\tbox_create(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_del": "\tbox_del(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_len": "\tbox_len(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_get": "\tbox_get(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_put": "\tbox_put(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_extract": "\tbox_extract(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_replace": "\tbox_replace(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_resize": "\tbox_resize(s, BS, TxnGroup[currentTxn], ctx);\n",
        "box_splice": "\tbox_splice(s, BS, TxnGroup[currentTxn], ctx);\n",
        # Inner transactions
        "itxn_begin": "\titxn_begin(s, ctx);\n",
        "itxn_submit": "\titxn_submit(BS, ctx);\n",
        "itxn_next": "\titxn_next(s, BS, ctx);\n",
        # Byte math
        "b+": "\tbmath_add(s);\n",
        "b-": "\tbmath_sub(s);\n",
        "b*": "\tbmath_mul(s);\n",
        "b/": "\tbmath_div(s);\n",
        "b%": "\tbmath_mod(s);\n",
        "b<": "\tbmath_lt(s);\n",
        "b>": "\tbmath_gt(s);\n",
        "b<=": "\tbmath_leq(s);\n",
        "b>=": "\tbmath_geq(s);\n",
        "b==": "\tbmath_eq(s);\n",
        "b!=": "\tbmath_neq(s);\n",
        "b|": "\tbmath_or(s);\n",
        "b&": "\tbmath_and(s);\n",
        "b^": "\tbmath_xor(s);\n",
        "b~": "\tbmath_neg(s);\n",
        "bsqrt": "\tbmath_sqrt(s);\n",
        # Misc
        "balance": "\tbalance_op(s, BS, TxnGroup[currentTxn]);\n",
        "min_balance": "\tmin_balance_op(s, BS, TxnGroup[currentTxn]);\n",
        "loads": "\tloads(s, ctx);\n",
        "stores": "\tstores(s, ctx);\n",
        "args": "\targs(s, ctx);\n",
        "gaids": "\tgaids_op(s);\n",
    }

    def _visit_zero_argument_opcode(self, node):
        op = self._opcode_text(node)

        # Check if this is a state op that can consume a pending key
        if self._pending_key is not None:
            init, nbytes = self._pending_key
            if op in self._GLOBAL_STATE_OPS and init in self._global_key_map:
                self._pending_key = None
                self._emit_fused_global_op(op, init, nbytes)
                return
            if op in self._LOCAL_STATE_OPS and init in self._local_key_map:
                self._pending_key = None
                self._emit_fused_local_op(op, init, nbytes)
                return
            # Not a matching state op — flush the pending key as normal pushbytes
            self._flush_pending_key()

        # Handle intc_N / bytec_N / arg_N shorthand
        if op.startswith("intc_"):
            idx = int(op.split("_")[1])
            if self._intcblock is not None and idx < len(self._intcblock):
                val = self._intcblock[idx]
                n_lit = f"{val}ULL" if val > 0x7FFFFFFF else str(val)
                self._emit(f"\tpushint(s, {n_lit});\n")
            else:
                self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //intc_{idx} without intcblock\n")
            return
        if op.startswith("bytec_"):
            idx = int(op.split("_")[1])
            if self._bytecblock is not None and idx < len(self._bytecblock):
                init = self._bytecblock[idx]
                # Defer if this key is used with a state op
                if init in self._global_key_map or init in self._local_key_map:
                    self._pending_key = (init, self._init_list_byte_count(init))
                    return
                self._emit_inline_pushbytes(init)
            else:
                self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //bytec_{idx} without bytecblock\n")
            return
        if op.startswith("arg_"):
            idx = op.split("_")[1]
            self._emit(f"\targ(s, ctx, {idx});\n")
            return

        # Handle retsub: jump to the single dispatch block
        if op == "retsub":
            self._emit(f"\tgoto {self._label_prefix}_retsub_dispatch;\n")
            return

        if op == "return":
            self._emit(f"\tgoto {self._label_prefix}_contract_end;\n")
            return
        if op == "err":
            self._emit(f"\t{{ err(); goto {self._label_prefix}_contract_end; }}\n")
            return

        if op in self._ZERO_ARG_MAP:
            self._emit_op(self._ZERO_ARG_MAP[op])
        else:
            # Unsupported opcode: emit panic so CBMC correctly flags this path
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: {op}\n")

    def _visit_single_numeric_argument_opcode(self, node):
        op = self._opcode_text(node)
        n = self._numeric_arg(node)

        # Use ULL suffix for large uint64 constants to avoid C++ warnings
        n_lit = f"{n}ULL" if n > 0x7FFFFFFF else str(n)

        single_num_map = {
            "pushint": f"\tpushint(s, {n_lit});\n",
            "int": f"\tpushint(s, {n_lit});\n",
            "popn": f"\ts.currentSize -= {n};\n",
            "dupn": self._unroll_dupn(n),
            "dig": f"\tdig(s, {n});\n",
            "bury": f"\tbury(s, {n});\n",
            "cover": self._unroll_cover(n),
            "uncover": self._unroll_uncover(n),
            "frame_dig": f"\tframe_dig(s, ctx, {n});\n",
            "frame_bury": f"\tframe_bury(s, ctx, {n});\n",
            "load": f"\tload(s, ctx, {n});\n",
            "store": f"\tstore(s, ctx, {n});\n",
            "arg": f"\targ(s, ctx, {n});\n",
            "replace2": f"\treplace2(s, {n});\n",
            "gloads": f"\tgloads_op(s, {n});\n",
            "gaid": f"\tgaid_op(s, {n});\n",
        }

        if op == "intc":
            if self._intcblock is not None and n < len(self._intcblock):
                val = self._intcblock[n]
                v_lit = f"{val}ULL" if val > 0x7FFFFFFF else str(val)
                self._emit(f"\tpushint(s, {v_lit});\n")
            else:
                self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //intc {n} without intcblock\n")
            return
        if op == "bytec":
            if self._bytecblock is not None and n < len(self._bytecblock):
                init = self._bytecblock[n]
                # Defer if this key is used with a state op
                if init in self._global_key_map or init in self._local_key_map:
                    self._pending_key = (init, self._init_list_byte_count(init))
                    return
                self._emit_inline_pushbytes(init)
            else:
                self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //bytec {n} without bytecblock\n")
            return

        if op in single_num_map:
            self._emit_op(single_num_map[op])
        else:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: {op} {n}\n")

    def _visit_double_numeric_argument_opcode(self, node):
        op = self._opcode_text(node)
        args = self._numeric_args(node)
        if len(args) < 2:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: {op} (missing args)\n")
            return
        a, b = args[0], args[1]

        if op == "extract":
            self._emit_op(f"\textract(s, {a}, {b});\n")
        elif op == "substring":
            self._emit_op(f"\tsubstring(s, {a}, {b});\n")
        elif op == "proto":
            self._emit_op(f"\tproto(s, ctx, {a}, {b});\n")
        elif op == "replace2":
            self._emit_op(f"\treplace2(s, {a});\n")
        elif op == "gload":
            self._emit_op(f"\tgload_op(s, {a}, {b});\n")
        else:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: {op} {a} {b}\n")

    def _visit_pushbytes_opcode(self, node):
        init = self._bytes_arg(node)
        if init in self._global_key_map or init in self._local_key_map:
            self._pending_key = (init, self._init_list_byte_count(init))
            return
        self._emit_inline_pushbytes(init)

    # Note: _visit_pushbytess_opcode is defined again below (overrides this).

    def _visit_intcblock_opcode(self, node):
        args = self._numeric_args(node)
        self._intcblock = args
        # No runtime code — lookups resolved at transpile time

    def _visit_bytecblock_opcode(self, node):
        args = self._bytes_args(node)
        self._bytecblock = args
        # No runtime code — lookups resolved at transpile time

    def _visit_intc_opcode(self, node):
        n = self._numeric_arg(node)
        if self._intcblock is not None and n < len(self._intcblock):
            val = self._intcblock[n]
            v_lit = f"{val}ULL" if val > 0x7FFFFFFF else str(val)
            self._emit(f"\tpushint(s, {v_lit});\n")
        else:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //intc {n} without intcblock\n")

    def _visit_b_opcode(self, node):
        label = self._label_arg(node)
        self._emit(f"\tgoto {self._label(label)};\n")

    def _visit_bz_opcode(self, node):
        label = self._label_arg(node)
        self._emit(f"\tif(s.pop().value == 0) goto {self._label(label)};\n")

    def _visit_bnz_opcode(self, node):
        label = self._label_arg(node)
        self._emit(f"\tif(s.pop().value != 0) goto {self._label(label)};\n")

    def _visit_callsub_opcode(self, node):
        label = self._label_arg(node)
        self._emit(f"\t_csub[_csub_sp++] = {self.callsub_n};\n")
        self._emit(f"\tgoto {self._label(label)};\n")
        self._emit(f"{self._label_prefix}callsub_{self.callsub_n}:\n")
        self.callsub_n += 1

    def _visit_switch_opcode(self, node):
        labels = self._label_args(node)
        self._emit(generate_switch_branches(labels, self._label_prefix))

    def _visit_match_opcode(self, node):
        labels = self._label_args(node)
        self._emit(generate_match_branches(labels, self._label_prefix))

    def _visit_txn_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\ttxn_field(s, TxnGroup[currentTxn], {field});\n")

    def _visit_txna_opcode(self, node):
        field = self._field_name(node)
        n = self._numeric_arg(node)
        self._emit(f"\ttxna_field(s, TxnGroup[currentTxn], {field}, {n});\n")

    def _visit_txnas_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\ttxnas(s, TxnGroup[currentTxn], {field});\n")

    def _visit_gtxn_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        if len(args) >= 1:
            self._emit(f"\tgtxn_field(s, TxnGroup, {args[0]}, {field});\n")
        else:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: gtxn (missing args)\n")

    def _visit_gtxna_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        if len(args) >= 2:
            self._emit(f"\tgtxna_field(s, TxnGroup, {args[0]}, {field}, {args[1]});\n")
        else:
            self._emit(f"\t{{ avm_panic(); goto {self._label_prefix}_contract_end; }} //UNSUPPORTED: gtxna (missing args)\n")

    def _visit_gtxns_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tgtxns_field(s, TxnGroup, {field});\n")

    def _visit_gtxnsa_opcode(self, node):
        field = self._field_name(node)
        n = self._numeric_arg(node)
        self._emit(f"\tgtxnsa(s, TxnGroup, {field}, {n});\n")

    def _visit_gtxnas_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        txn_idx = args[0] if args else 0
        self._emit(f"\tgtxnas(s, TxnGroup, {txn_idx}, {field});\n")

    def _visit_gtxnsas_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tgtxnsas(s, TxnGroup, {field});\n")

    def _visit_global_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tglobal_field(s, BS, ctx, GF_{field});\n")

    def _visit_itxn_field_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\titxn_field(s, ctx, {field});\n")

    def _visit_itxn_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\titxn_field_read(s, ctx, {field});\n")

    def _visit_itxna_opcode(self, node):
        field = self._field_name(node)
        n = self._numeric_arg(node)
        self._emit(f"\titxna_field_read(s, ctx, {field}, {n});\n")

    def _visit_gitxn_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        # gitxn <group_index> <field> — read field from inner txn at group index
        group_idx = args[0] if args else 0
        self._emit(f"\tgitxn_field(s, ctx, {group_idx}, {field});\n")

    def _visit_gitxna_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        # gitxna <group_index> <field> <array_index>
        group_idx = args[0] if len(args) > 0 else 0
        array_idx = args[1] if len(args) > 1 else 0
        self._emit(f"\tgitxna_field(s, ctx, {group_idx}, {field}, {array_idx});\n")

    def _visit_itxnas_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\titxnas(s, ctx, {field});\n")

    def _visit_gitxnas_opcode(self, node):
        args = self._numeric_args(node)
        field = self._field_name(node)
        group_idx = args[0] if args else 0
        self._emit(f"\tgitxnas(s, ctx, {group_idx}, {field});\n")

    def _visit_acct_params_get_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tacct_params_get(s, BS, TxnGroup[currentTxn], ctx, {field});\n")

    def _visit_app_params_get_opcode(self, node):
        field = self._field_name(node)
        # Map AppAddress field name to avoid collision with C++ enum
        cpp_field = "AppAddress_field" if field == "AppAddress" else field
        self._emit(f"\tapp_params_get(s, BS, ctx, {cpp_field});\n")

    def _visit_asset_holding_get_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tasset_holding_get(s, BS, TxnGroup[currentTxn], ctx, {field}_field);\n")

    def _visit_json_ref_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tjson_ref(s, {field});\n")

    def _visit_asset_params_get_opcode(self, node):
        field = self._field_name(node)
        self._emit(f"\tasset_params_get(s, BS, {field}_field);\n")

    def _visit_ecdsa_opcode(self, node):
        op = self._opcode_text(node)
        if op == "ecdsa_pk_recover":
            self._emit("\tecdsa_pk_recover(s);\n")
        elif op == "ecdsa_pk_decompress":
            self._emit("\tecdsa_pk_decompress(s);\n")
        elif op == "ecdsa_verify":
            self._emit("\tecdsa_verify(s);\n")
        self._emit("\tAVM_BAIL_ON_PANIC();\n")

    def _visit_load_opcode(self, node):
        n = self._numeric_arg(node)
        self._emit(f"\tload(s, ctx, {n});\n")

    def _visit_store_opcode(self, node):
        n = self._numeric_arg(node)
        self._emit(f"\tstore(s, ctx, {n});\n")

    def _visit_pushints_opcode(self, node):
        args = self._numeric_args(node)
        for a in args:
            self._emit(f"\tpushint(s, {a});\n")

    def _visit_pushbytess_opcode(self, node):
        args = self._bytes_args(node)
        for a in args:
            self._emit_inline_pushbytes(a)

    def _visit_error(self, node):
        """Try to recover from ERROR nodes (grammar gaps)."""
        text = node.text.decode().strip()
        self._emit(f"\t//PARSE ERROR: {text}\n")

    # -- main entry point ---------------------------------------------------

    def transpile(self, source: str) -> str:
        """Parse and transpile TEAL source code to C++."""
        preprocessed = _preprocess_teal(source)
        tree = _PARSER.parse(preprocessed.encode())
        root = tree.root_node

        self.callsub_total = self._count_callsubs(root)
        self.callsub_n = 0
        self.output = ""
        self._global_key_map = {}
        self._local_key_map = {}
        self._pending_key = None

        # First pass: collect static keys for direct-indexed state access
        self._collect_static_keys(root)

        # Declare callsub stack as local variables
        if self.callsub_total > 0:
            self._emit("\tuint32_t _csub[32]; uint32_t _csub_sp = 0;\n")

        self._visit_source(root)

        # Flush any trailing pending key
        self._flush_pending_key()

        # Emit single retsub dispatch block at end (if contract uses callsub)
        if self.callsub_total > 0:
            self._emit(generate_retsub_dispatch(self.callsub_total, self._label_prefix))

        return self.output


# ---------------------------------------------------------------------------
# File-level transpilation (parse_contract kept for backward compat)
# ---------------------------------------------------------------------------

def parse_contract(filename: str) -> str:
    """Read a TEAL file and return its source text."""
    with open(filename, "r") as f:
        return f.read()


def transpile_contract(source: str, label_prefix: str = "") -> str:
    """Transpile TEAL source to C++ using tree-sitter."""
    t = TEALTranspiler(label_prefix=label_prefix)
    return t.transpile(source)


def transpile_contract_with_keys(source: str) -> tuple[str, dict[str, int], dict[str, int]]:
    """Transpile TEAL source and return (code, global_key_map, local_key_map).

    The key maps are {init_list_str: sequential_index} for each static key
    discovered during transpilation. Templates should use gs_put_idx/ls_put_idx
    with these indices to ensure consistency with transpiled indexed access.
    """
    t = TEALTranspiler()
    code = t.transpile(source)
    return code, dict(t._global_key_map), dict(t._local_key_map)


# LogicSig-only opcodes (present in LogicSigs, forbidden in app calls)
_LSIG_OPCODES = {"arg", "arg_0", "arg_1", "arg_2", "arg_3", "args"}

# Application-only opcodes (forbidden in LogicSigs)
_APP_OPCODES = {
    "app_opted_in", "app_local_get", "app_local_get_ex",
    "app_global_get", "app_global_get_ex",
    "app_local_put", "app_global_put", "app_local_del", "app_global_del",
    "app_params_get", "itxn_begin", "itxn_field", "itxn_submit", "itxn_next",
    "gitxn", "gitxna", "gitxnas",
    "box_create", "box_extract", "box_replace", "box_del",
    "box_len", "box_get", "box_put", "box_resize", "box_splice",
}


def _key_label(key_bytes: list[int], prefix: str) -> str:
    """Generate a C identifier from key bytes, e.g. GKEY_counter or LKEY_0x01ff."""
    # Try to decode as ASCII
    try:
        name = bytes(key_bytes).decode("ascii")
        if name.isidentifier():
            return f"{prefix}_{name}"
    except (ValueError, UnicodeDecodeError):
        pass
    # Fall back to hex
    hex_str = "".join(f"{b:02x}" for b in key_bytes)
    return f"{prefix}_0x{hex_str}"


def detect_contract_mode(source: str) -> str:
    """Detect whether a TEAL source is a LogicSig or application call.

    Heuristics (in priority order):
    1. If source contains 'arg' opcodes and NO app-only opcodes → "logicsig"
    2. If source contains app-only opcodes → "application"
    3. If filename/comments indicate logicsig → "logicsig"
    4. Default → "application"
    """
    # Tokenize: extract opcode names from non-comment, non-label lines
    opcodes_found: set[str] = set()
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        # Skip labels (end with :)
        if line.endswith(":"):
            continue
        parts = line.split()
        if parts:
            opcodes_found.add(parts[0])

    has_lsig = bool(opcodes_found & _LSIG_OPCODES)
    has_app = bool(opcodes_found & _APP_OPCODES)

    if has_lsig and not has_app:
        return "logicsig"
    if has_app:
        return "application"

    # Check comments for "logicsig" or "lsig" hint
    lower = source.lower()
    if "logicsig" in lower or "// lsig" in lower or "# lsig" in lower:
        return "logicsig"

    return "application"


def write_verify(
    contract_path: str,
    template_path: str | None = None,
    out_path: str | None = None,
    app_id: int = 1,
    properties: list[str] | None = None,
    property_file: str | None = None,
    defines: dict[str, int | str] | None = None,
    setup_code: str | None = None,
    inner_contracts: dict[int, str] | None = None,
    _transpiled: tuple[str, dict[str, int], dict[str, int]] | None = None,
) -> str:
    """
    Generate a CBMC verification harness from a TEAL contract.

    Args:
        contract_path: Path to a .teal file.
        template_path: Override the verification template.
        out_path: Override the output file.
        app_id: ApplicationID for the contract (default: 1).
        properties: List of C++ property expressions to verify.
            Each expression can reference `ctx` (VerifyContext).
        property_file: Path to a .cpp file with property functions to include.
        defines: Override #define values in the template (e.g. {"CBMC_STACK_MAX": 24}).
        setup_code: C++ code to inject at METHOD_CONSTRAINT_PLACEHOLDER.
        inner_contracts: Map of {app_id: teal_path} for secondary contracts
            that can be called via inner app call dispatch.

    Returns the output file path.
    """
    project_root = Path(__file__).parent.parent
    outp = Path(out_path) if out_path else project_root / "generated" / "verify.generated.cpp"
    tpl_path = (
        Path(template_path)
        if template_path
        else project_root / "engine" / "AVM_verify_template.cpp"
    )

    if not tpl_path.exists():
        raise FileNotFoundError(f"Template file not found: {tpl_path}")

    tpl_text = tpl_path.read_text(encoding="utf-8")

    # Enable inner dispatch when secondary contracts are provided
    if inner_contracts:
        tpl_text = "#define CBMC_INNER_DISPATCH\n" + tpl_text

    # Apply template bound overrides
    if defines:
        import re as _re
        for key, val in defines.items():
            pattern = rf"^#define\s+{_re.escape(key)}\s+\S+"
            if _re.search(pattern, tpl_text, flags=_re.MULTILINE):
                tpl_text = _re.sub(
                    pattern,
                    f"#define {key} {val}",
                    tpl_text,
                    count=1,
                    flags=_re.MULTILINE,
                )
            else:
                # Insert new define before the first #include
                tpl_text = tpl_text.replace(
                    '#include "cbmc_avm.h"',
                    f"#define {key} {val}\n" + '#include "cbmc_avm.h"',
                    1,
                )

    # Build properties section
    prop_section = ""
    if property_file:
        prop_section = Path(property_file).read_text(encoding="utf-8")

    # Build property checks
    prop_checks = ""
    if properties:
        for i, prop in enumerate(properties):
            prop_checks += f"    VERIFY_ASSERT({prop}); // property_{i}\n"

    # Transpile the contract (CBMC mode for verification harnesses)
    if _transpiled is not None:
        code, gkey_map, lkey_map = _transpiled
    else:
        source = parse_contract(contract_path)
        code, gkey_map, lkey_map = transpile_contract_with_keys(source)

    # Inject key index defines so templates/setup_code can use gs_put_idx/ls_put_idx
    if gkey_map or lkey_map:
        key_defs = "// Key index defines (generated by transpiler)\n"
        for init, idx in sorted(gkey_map.items(), key=lambda x: x[1]):
            key_bytes = TEALTranspiler._init_list_to_bytes(init)
            label = _key_label(key_bytes, "GKEY")
            key_defs += f"#define {label} {idx}\n"
        for init, idx in sorted(lkey_map.items(), key=lambda x: x[1]):
            key_bytes = TEALTranspiler._init_list_to_bytes(init)
            label = _key_label(key_bytes, "LKEY")
            key_defs += f"#define {label} {idx}\n"
        if gkey_map:
            key_defs += f"#define CBMC_NUM_GLOBAL_KEYS {len(gkey_map)}\n"
        if lkey_map:
            key_defs += f"#define CBMC_NUM_LOCAL_KEYS {len(lkey_map)}\n"
        # Insert after //Function prototypes so they're visible to setup_code and properties
        tpl_text = tpl_text.replace(
            "//Function prototypes\n",
            f"//Function prototypes\n{key_defs}",
            1,
        )

    # Build forward declarations for secondary contracts
    inner_protos = ""
    if inner_contracts:
        for sec_id in inner_contracts:
            inner_protos += (
                f"void contract_{sec_id}(Stack& s, BlockchainState& BS, "
                f"EvalContext& ctx, Txn* TxnGroup, uint8_t currentTxn);\n"
            )

    # Inject into template: inline the contract code at the placeholder
    tpl_text = tpl_text.replace(
        "//Function prototypes\n",
        f"//Function prototypes\n{inner_protos}",
        1,
    )
    tpl_text = tpl_text.replace(
        "//PROPERTIES_PLACEHOLDER",
        prop_section,
        1,
    )
    tpl_text = tpl_text.replace(
        "//CONTRACT_CALL_PLACEHOLDER",
        f"    // --- Transpiled contract code ---\n{code}",
        1,
    )
    tpl_text = tpl_text.replace(
        "//PROPERTY_CHECKS_PLACEHOLDER",
        prop_checks if prop_checks else "    // No properties specified",
        1,
    )
    if setup_code:
        tpl_text = tpl_text.replace(
            "//METHOD_CONSTRAINT_PLACEHOLDER",
            setup_code,
            1,
        )

    # Append secondary contract functions and dispatch
    if inner_contracts:
        tpl_text += "\n\n"
        # Transpile and wrap each secondary contract.
        # goto-cc requires globally unique labels across all functions,
        # so we redefine AVM_BAIL_ON_PANIC to use a per-contract label.
        for sec_id, sec_path in inner_contracts.items():
            sec_source = parse_contract(sec_path)
            prefix = f"c{sec_id}_"
            sec_code = transpile_contract(sec_source, label_prefix=prefix)
            label = f"{prefix}_contract_end"
            tpl_text += (
                f"#undef AVM_BAIL_ON_PANIC\n"
                f"#define AVM_BAIL_ON_PANIC() do {{ if (__avm_panicked) goto {label}; }} while(0)\n"
                f"void contract_{sec_id}(Stack& s, BlockchainState& BS, "
                f"EvalContext& ctx, Txn* TxnGroup, uint8_t currentTxn) {{\n"
                f"{sec_code}"
                f"{label}: ;\n"
                f"}}\n\n"
            )
        # Restore original macro
        tpl_text += (
            "#undef AVM_BAIL_ON_PANIC\n"
            "#define AVM_BAIL_ON_PANIC() do { if (__avm_panicked) goto _contract_end; } while(0)\n\n"
        )

        # Generate dispatch function
        tpl_text += _generate_dispatch_function(inner_contracts)

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(tpl_text, encoding="utf-8")

    return str(outp.resolve())


def _generate_app_address(app_id: int) -> list[int]:
    """Generate a deterministic 32-byte address for an app ID.

    Encodes app_id as big-endian in the last 8 bytes, with 0xAA marker at byte 0.
    This is a model-level convention, not the real Algorand address derivation.
    """
    addr = [0] * 32
    addr[0] = 0xAA  # marker: this is an app address
    for j in range(8):
        addr[31 - j] = (app_id >> (j * 8)) & 0xFF
    return addr


def _generate_creator_address(app_id: int) -> list[int]:
    """Generate a deterministic 32-byte creator address for an app ID.

    Encodes app_id as big-endian in the last 8 bytes, with 0xCC marker at byte 0.
    Distinct from app address (0xAA marker) to avoid collisions.
    """
    addr = [0] * 32
    addr[0] = 0xCC  # marker: this is a creator address
    for j in range(8):
        addr[31 - j] = (app_id >> (j * 8)) & 0xFF
    return addr


def _generate_dispatch_function(
    inner_contracts: dict[int, str],
) -> str:
    """Generate the _cbmc_dispatch_inner_app function for multi-contract dispatch.

    Features:
    - Per-app deterministic addresses (CurrentApplicationAddress, CreatorAddress)
    - Per-app global state isolation (swap BS.globals around inner call)
    - Atomic rollback on inner rejection
    """
    all_ids = list(inner_contracts.keys())

    # Generate deterministic address and creator constants
    addr_decls = ""
    addr_cases = ""
    creator_cases = ""
    for sec_id in all_ids:
        addr = _generate_app_address(sec_id)
        arr = ", ".join(str(b) for b in addr)
        addr_decls += f"static const uint8_t _app_addr_{sec_id}[32] = {{{arr}}};\n"
        addr_cases += f"        case {sec_id}: _cbmc_bytecopy(inner_ctx.CurrentApplicationAddress, _app_addr_{sec_id}, 32); break;\n"

        creator = _generate_creator_address(sec_id)
        carr = ", ".join(str(b) for b in creator)
        addr_decls += f"static const uint8_t _creator_addr_{sec_id}[32] = {{{carr}}};\n"
        creator_cases += f"        case {sec_id}: _cbmc_bytecopy(inner_ctx.CreatorAddress, _creator_addr_{sec_id}, 32); break;\n"

    # Per-app globals: static storage for each inner app
    globals_decls = ""
    globals_swap_in = ""
    globals_save_back = ""
    globals_rollback = ""
    for sec_id in all_ids:
        globals_decls += f"static GlobalState _app_globals_{sec_id};\n"
        globals_decls += f"static bool _app_globals_{sec_id}_inited = false;\n"
        globals_swap_in += (
            f"        case {sec_id}:\n"
            f"            if (!_app_globals_{sec_id}_inited) {{ gs_init(_app_globals_{sec_id}); _app_globals_{sec_id}_inited = true; }}\n"
            f"            BS.globals = _app_globals_{sec_id}; break;\n"
        )
        globals_save_back += f"        case {sec_id}: _app_globals_{sec_id} = BS.globals; break;\n"
        globals_rollback += f"        case {sec_id}: _app_globals_{sec_id} = BS_snapshot.globals; break;\n"

    cases = ""
    for sec_id in all_ids:
        cases += f"        case {sec_id}: contract_{sec_id}(inner_s, BS, inner_ctx, inner_group, 0); break;\n"

    return f"""
static uint32_t _inner_depth = 0;

// Deterministic addresses for inner apps
{addr_decls}
// Per-app global state (persists across calls, rolled back on rejection)
{globals_decls}
void _cbmc_dispatch_inner_app(BlockchainState& BS, Txn& txn) {{
    if (_inner_depth >= CBMC_MAX_INNER_DEPTH) return;
    _inner_depth++;

    bool outer_panicked = __avm_panicked;
    __avm_panicked = false;

    // Save outer globals, swap in inner app's globals
    GlobalState _outer_globals = BS.globals;
    switch (txn.ApplicationID) {{
{globals_swap_in}        default: gs_init(BS.globals); break;
    }}

    // Snapshot state (now with inner globals in BS.globals)
    BlockchainState BS_snapshot = BS;

    Stack inner_s;
    stack_init(inner_s);
    EvalContext inner_ctx;
    ctx_init(inner_ctx);
    inner_ctx.CurrentApplicationID = txn.ApplicationID;

    // Set the inner app's deterministic address and creator
    switch (txn.ApplicationID) {{
{addr_cases}        default: break;
    }}
    switch (txn.ApplicationID) {{
{creator_cases}        default: break;
    }}

    Txn inner_group[1];
    inner_group[0] = txn;

    switch (txn.ApplicationID) {{
{cases}        default: avm_panic(); break;
    }}

    // Determine accept/reject
    bool accepted = !__avm_panicked && inner_s.currentSize > 0
                    && !inner_s.stack[inner_s.currentSize - 1]._is_bytes
                    && inner_s.stack[inner_s.currentSize - 1].value != 0;

    if (accepted) {{
        // Persist inner globals
        switch (txn.ApplicationID) {{
{globals_save_back}            default: break;
        }}
    }} else {{
        // Rollback inner globals
        switch (txn.ApplicationID) {{
{globals_rollback}            default: break;
        }}
        BS = BS_snapshot;
    }}

    // Restore outer globals (always — they were never part of the inner execution)
    BS.globals = _outer_globals;

    __avm_panicked = outer_panicked || !accepted;
    _inner_depth--;
}}
"""




# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TEAL to C++ CBMC verification transpiler")
    parser.add_argument("contract", help="TEAL contract file")
    parser.add_argument("--template", type=str, default=None, help="Template file path")
    parser.add_argument("--out", type=str, default=None, help="Output file path")
    parser.add_argument("--property", type=str, action="append", default=None,
                        help="C++ property expression (can repeat)")
    parser.add_argument("--property-file", type=str, default=None,
                        help="File with property definitions")
    parser.add_argument("--app-id", type=int, default=1, help="Application ID for verification")
    args = parser.parse_args()

    result = write_verify(
        args.contract,
        args.template,
        args.out,
        app_id=args.app_id,
        properties=args.property,
        property_file=args.property_file,
    )
    print(f"Generated: {result}")
