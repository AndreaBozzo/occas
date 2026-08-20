"""Wrapper around the official PX4 ``download_logs.py``, with a retrieval manifest.

This module **orchestrates**; it does not talk to the log API itself and it does not
parse anything. The upstream script is the interface to ``logs.px4.io``; what this adds
is the part the project needs and upstream does not provide: a record of exactly what
was retrieved, when, under which terms, so that a later manifest can point at it.

Blocking precondition (gate G1): the personal-data section of
``docs/01-source-audit.md`` is unresolved. Access and rate limits are now answered --
the upstream client documents 10 requests/minute and treats excess as an IP block, and
``logs.px4.io/robots.txt`` disallows crawling outright -- but B1-B5 are not. This
script refuses to run while that section is marked unresolved, or until
``--acknowledge-unaudited`` is passed for a deliberate small sample.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT = REPO_ROOT / "docs" / "01-source-audit.md"
BLOCKING_MARKER = "B-status: UNRESOLVED"

# CC-BY attribution travels with every artifact derived from these logs.
PX4_ATTRIBUTION = "Flight logs from PX4 Flight Review (logs.px4.io), CC-BY PX4."


def audit_is_blocking() -> bool:
    """True while the personal-data section of the audit is unresolved (gate G1)."""
    return AUDIT.exists() and BLOCKING_MARKER in AUDIT.read_text(encoding="utf-8")


def write_retrieval_record(out_dir: Path, argv: list[str], returncode: int) -> Path:
    """Record what was asked for and when. Retrieval metadata cannot be reconstructed later."""
    retrieved_at = datetime.now(UTC).isoformat()
    record = {
        "source": "px4_flight_review",
        "source_url": "https://logs.px4.io/browse",
        "retrieved_at": retrieved_at,
        "licence": "CC-BY-4.0",
        "attribution": PX4_ATTRIBUTION,
        "command": argv,
        "returncode": returncode,
        "audit_status": "personal-data section unresolved" if audit_is_blocking() else "resolved",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"retrieval-{retrieved_at.replace(':', '')}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--upstream",
        type=Path,
        required=True,
        help="Path to the official PX4 download_logs.py.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=REPO_ROOT / "data" / "raw", help="Download destination."
    )
    parser.add_argument(
        "--acknowledge-unaudited",
        action="store_true",
        help="Proceed while docs/01-source-audit.md is unanswered. For a small deliberate "
        "sample only; nothing retrieved this way may be published.",
    )
    parser.add_argument(
        "upstream_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to the upstream script verbatim.",
    )
    args = parser.parse_args(argv)

    if audit_is_blocking() and not args.acknowledge_unaudited:
        print(
            "Refusing to download: the personal-data section of "
            "docs/01-source-audit.md is UNRESOLVED (gate G1).\n"
            "Access and rate limits are answered; B1-B5 are not. Answer them, or "
            "pass --acknowledge-unaudited to pull a small deliberate sample that "
            "must not be published.",
            file=sys.stderr,
        )
        return 2

    if not args.upstream.exists():
        print(f"Upstream script not found: {args.upstream}", file=sys.stderr)
        return 2

    command = [sys.executable, str(args.upstream), *args.upstream_args]
    completed = subprocess.run(command, check=False)
    record = write_retrieval_record(args.out_dir, command, completed.returncode)
    print(f"Retrieval record: {record}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
