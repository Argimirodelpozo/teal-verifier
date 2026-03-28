"""
Pytest suite for Tealer-style CodeQL detections.

For each detection, runs the query against:
  - A vulnerable contract (expects >= 1 result)
  - A fixed contract (expects 0 results)

Prerequisites:
  - CodeQL CLI on PATH
  - Databases already built (run `build_test_databases.sh` first)
"""

from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DETECTIONS_DIR = Path(__file__).resolve().parent
TEST_CONTRACTS_DIR = DETECTIONS_DIR / "test-contracts"
SEARCH_PATH = str(REPO_ROOT / ".codeql-extractors")


def run_query(query_path: Path, database_path: Path) -> list[dict]:
    """Run a CodeQL query and return parsed CSV rows."""
    with tempfile.TemporaryDirectory() as tmp:
        bqrs = Path(tmp) / "result.bqrs"
        csv_path = Path(tmp) / "result.csv"

        subprocess.run(
            [
                "codeql", "query", "run",
                "--database", str(database_path),
                str(query_path),
                "--output", str(bqrs),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "codeql", "bqrs", "decode",
                "--format=csv",
                "--output", str(csv_path),
                str(bqrs),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)


def build_database(source_dir: Path, db_path: Path) -> None:
    """Build a CodeQL database for a TEAL source directory."""
    subprocess.run(
        [
            "codeql", "database", "create",
            str(db_path),
            "--overwrite",
            "-l", "teal",
            "-s", str(source_dir),
            "--search-path", SEARCH_PATH,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def ensure_database(detection_name: str, variant: str) -> Path:
    """Ensure a test database exists for the given detection and variant."""
    db_path = TEST_CONTRACTS_DIR / detection_name / f"{variant}-db"
    src_path = TEST_CONTRACTS_DIR / detection_name / f"{variant}-src"

    if not db_path.exists():
        if not src_path.exists():
            # Fall back to using the main contract directory
            src_path = TEST_CONTRACTS_DIR / detection_name
        build_database(src_path, db_path)

    return db_path


# Detection configurations: (detection_dir, query_file)
DETECTIONS = [
    ("is-deletable", "isDeletable.ql"),
    ("is-updatable", "isUpdatable.ql"),
    ("unprotected-deletable", "unprotectedDeletable.ql"),
    ("unprotected-updatable", "unprotectedUpdatable.ql"),
    ("group-size-check", "groupSizeCheck.ql"),
    ("can-close-account", "canCloseAccount.ql"),
    ("can-close-asset", "canCloseAsset.ql"),
    ("missing-fee-check", "missingFeeCheck.ql"),
    ("rekey-to", "rekeyTo.ql"),
    ("constant-gtxn", "constantGtxn.ql"),
    ("self-access", "selfAccess.ql"),
    ("sender-access", "senderAccess.ql"),
]


@pytest.mark.parametrize(
    "detection_dir,query_file",
    DETECTIONS,
    ids=[d[0] for d in DETECTIONS],
)
def test_vuln_detected(detection_dir: str, query_file: str) -> None:
    """Vulnerable contract should produce at least one finding."""
    db_path = ensure_database(detection_dir, "vuln")
    query_path = DETECTIONS_DIR / query_file
    rows = run_query(query_path, db_path)
    assert len(rows) > 0, (
        f"{detection_dir}/vuln: expected findings but got 0. "
        f"Query: {query_file}"
    )


@pytest.mark.parametrize(
    "detection_dir,query_file",
    DETECTIONS,
    ids=[d[0] for d in DETECTIONS],
)
def test_fixed_clean(detection_dir: str, query_file: str) -> None:
    """Fixed contract should produce zero findings."""
    db_path = ensure_database(detection_dir, "fixed")
    query_path = DETECTIONS_DIR / query_file
    rows = run_query(query_path, db_path)
    assert len(rows) == 0, (
        f"{detection_dir}/fixed: expected 0 findings but got {len(rows)}. "
        f"Query: {query_file}, Results: {rows}"
    )
