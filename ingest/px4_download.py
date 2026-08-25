"""Wrapper around the official PX4 ``download_logs.py``, with a retrieval manifest.

This module **orchestrates**; it does not talk to the log API itself and it does not
parse anything. The upstream script is the interface to ``logs.px4.io``; what this adds
is the part the project needs and upstream does not provide: a record of exactly what
was retrieved, when, under which terms, so that a later manifest can point at it.

Blocking precondition (gate G1): ``docs/01-source-audit.md`` carries a dedicated
``G1-status`` line, and this script refuses to run unless it says ``CLEARED`` -- or
until ``--acknowledge-unaudited`` is passed for a deliberate small sample. Access and
rate limits are answered (10 requests/minute, ``robots.txt`` disallows crawling); B1-B5
now have provisional answers in ``docs/07-personal-data.md``, which is not the same as
the gate being cleared: that needs the controller's sign-off, a privacy notice and a
DPIA. The *screening* is done -- ``docs/08-dpia-screening.md``, 2026-08-25 -- and it
concluded the assessment is required, and required **before** the first retrieval
rather than before publication (``adr/0011``). So this gate is not a formality that
publication will later satisfy; it is the thing standing in front of the download.

**The gate fails closed.** It reads one status line, and a missing file, a missing line
or an unrecognised value all block. The previous version searched for a phrase used in
the audit's prose, which meant rewriting that prose silently opened the gate -- which
is exactly what happened on 2026-08-24 when the B section was answered.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT = REPO_ROOT / "docs" / "01-source-audit.md"
# A dedicated flag, not a phrase from the prose: the gate must not turn on wording.
G1_STATUS = re.compile(r"^\*\*G1-status:\s*(NOT CLEARED|CLEARED)\*\*", re.MULTILINE)

# CC-BY attribution travels with every artifact derived from these logs.
PX4_ATTRIBUTION = "Flight logs from PX4 Flight Review (logs.px4.io), CC-BY PX4."


def audit_is_blocking() -> bool:
    """True while gate G1 is not cleared.

    Fails closed. Only an explicit ``**G1-status: CLEARED**`` line opens the gate;
    a missing audit, a missing line, or anything unrecognised blocks. Absence of
    evidence that publication is permitted is not evidence that it is.
    """
    if not AUDIT.exists():
        return True
    found = G1_STATUS.search(AUDIT.read_text(encoding="utf-8"))
    if found is None:
        return True
    return found.group(1) == "NOT CLEARED"


def upstream_command(upstream: Path, out_dir: Path, extra: list[str]) -> list[str]:
    """Build the upstream invocation, forcing its download folder to ``out_dir``.

    Without this the upstream default (``data/downloaded/``) wins and the logs land
    somewhere other than the retrieval record that describes them — a record that
    documents files it does not sit beside documents nothing. An explicit
    ``-d``/``--download-folder`` in ``extra`` is respected and warned about.
    """
    if any(arg in ("-d", "--download-folder") for arg in extra):
        print(
            "Warning: --download-folder passed through to the upstream script; the "
            "retrieval record will not sit beside the downloaded logs.",
            file=sys.stderr,
        )
        return [sys.executable, str(upstream), *extra]
    return [sys.executable, str(upstream), "--download-folder", str(out_dir), *extra]


def write_retrieval_record(
    out_dir: Path, argv: list[str], returncode: int, acknowledged: bool
) -> Path:
    """Record what was asked for and when. Retrieval metadata cannot be reconstructed later.

    ``publication_eligibility`` is the taint: anything pulled while gate G1 is
    unresolved must stay machine-readably unpublishable, so the constraint travels
    with the data instead of living only in a markdown file and a warning that
    scrolled past.
    """
    retrieved_at = datetime.now(UTC).isoformat()
    blocking = audit_is_blocking()
    record = {
        "source": "px4_flight_review",
        "source_url": "https://logs.px4.io/browse",
        "retrieved_at": retrieved_at,
        "licence": "CC-BY-4.0",
        "attribution": PX4_ATTRIBUTION,
        "command": argv,
        "returncode": returncode,
        "download_folder": str(out_dir),
        "audit_status": "personal-data section unresolved" if blocking else "resolved",
        "publication_eligibility": "blocked" if blocking else "eligible",
        "policy_reason": "G1_PERSONAL_DATA_UNRESOLVED" if blocking else None,
        "acknowledged_unaudited": acknowledged,
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
        help="Proceed while the personal-data section of docs/01-source-audit.md is "
        "unresolved. For a small deliberate sample only; the retrieval record marks "
        "everything pulled this way publication_eligibility=blocked.",
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

    command = upstream_command(args.upstream, args.out_dir, args.upstream_args)
    completed = subprocess.run(command, check=False)
    record = write_retrieval_record(
        args.out_dir, command, completed.returncode, args.acknowledge_unaudited
    )
    print(f"Retrieval record: {record}")
    if audit_is_blocking():
        print(
            "Retrieved under G1_PERSONAL_DATA_UNRESOLVED: these files are marked "
            "publication_eligibility=blocked and must not reach a published artifact.",
            file=sys.stderr,
        )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
