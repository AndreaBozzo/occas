"""Wrapper around the official PX4 ``download_logs.py``, with a retrieval manifest.

This module **orchestrates**; it does not talk to the log API itself and it does not
parse anything. The upstream script is the interface to ``logs.px4.io``; what this adds
is the part the project needs and upstream does not provide: a record of exactly what
was retrieved, when, under which terms, so that a later manifest can point at it.

Blocking precondition (gate G1): ``docs/01-source-audit.md`` carries a dedicated
``G1-status`` line, and this script refuses to run unless it says ``CLEARED``. There is
no override: an ``--acknowledge-unaudited`` flag existed until 2026-08-25, letting a
"deliberate small sample" past the gate with the record stamped blocked. It was removed
once the DPIA made clear that an acknowledgement is a record of a decision and not a
legal basis -- Article 35(1) requires the assessment before the processing, and a small
sample of geolocated logs is still processing. A gate with a documented way around it is
a suggestion.

A **second and independent** gate follows it: ``R5-encryption-at-rest`` in the DPIA. G1
asks whether the assessment was adopted; R5 asks whether one measure it relies on is
real. Clearing the first does not clear the second, because a signature must not stand
in for a disk.

Both were opened on 2026-08-25, on the DPIA adopted the same day
(``docs/09-dpia.md``, ``adr/0011``) and with EFS applied to ``data/``. Access and rate
limits were already answered: 10 requests/minute, and ``robots.txt`` disallows crawling,
so retrieval stays inside the maintainers' own documented limits (``adr/0012``).

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

from analysis.common import exclusions

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT = REPO_ROOT / "docs" / "01-source-audit.md"
DPIA = REPO_ROOT / "docs" / "09-dpia.md"
# A dedicated flag, not a phrase from the prose: the gate must not turn on wording.
G1_STATUS = re.compile(r"^\*\*G1-status:\s*(NOT CLEARED|CLEARED)\*\*", re.MULTILINE)
# The second gate, and it is independent of the first. The adopted DPIA lists encryption
# at rest among the measures addressing R5 -- a geolocated corpus on a personal machine --
# and on 2026-08-25 the machine was not encrypted. Rather than let an adopted assessment
# describe a measure that does not exist, the measure gates the code.
#
# A declaration rather than a detection: verifying BitLocker needs elevation that a
# download script must not have. manage-bde and the Win32_EncryptableVolume CIM class both
# refused without it. A declaration that stops the pipeline beats a sentence that stops
# nothing.
R5_ENCRYPTION = re.compile(
    r"^\s*\*\*R5-encryption-at-rest:\s*(NOT CONFIRMED|CONFIRMED)\*\*", re.MULTILINE
)

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


def encryption_is_blocking() -> bool:
    """True while encryption at rest is not confirmed in the adopted DPIA.

    Fails closed, for the same reason ``audit_is_blocking`` does and with the same
    shape: a missing file, a missing line or an unrecognised value all block. This gate
    is deliberately separate from G1. G1 asks whether the assessment exists and was
    adopted; this asks whether one specific measure the assessment relies on is real.
    Clearing the first does not clear the second, and collapsing them would let a
    signature stand in for a disk.
    """
    if not DPIA.exists():
        return True
    found = R5_ENCRYPTION.search(DPIA.read_text(encoding="utf-8"))
    if found is None:
        return True
    return found.group(1) == "NOT CONFIRMED"


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


def write_retrieval_record(out_dir: Path, argv: list[str], returncode: int) -> Path:
    """Record what was asked for and when. Retrieval metadata cannot be reconstructed later.

    ``publication_eligibility`` is the taint: anything pulled while gate G1 is
    unresolved must stay machine-readably unpublishable, so the constraint travels
    with the data instead of living only in a markdown file and a warning that
    scrolled past.
    """
    retrieved_at = datetime.now(UTC).isoformat()
    blocking = audit_is_blocking()
    record = {
        # Which Article 21 objections were in force when this was pulled -- a digest and
        # a count, never the identifiers. See analysis/common/exclusions.py for why the
        # list itself does not travel.
        "exclusions": exclusions.load().state(),
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
        "encryption_at_rest_confirmed": not encryption_is_blocking(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"retrieval-{retrieved_at.replace(':', '')}.json"
    # newline="\n": records are hashed and compared across machines; see adr/0010.
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
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
        "upstream_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to the upstream script verbatim.",
    )
    args = parser.parse_args(argv)

    if audit_is_blocking():
        print(
            "Refusing to download: docs/01-source-audit.md does not say "
            "**G1-status: CLEARED** (gate G1).\n"
            "There is no override. Clearing G1 means adopting the DPIA "
            "(docs/09-dpia.md) and setting that flag deliberately.",
            file=sys.stderr,
        )
        return 2

    if encryption_is_blocking():
        print(
            "Refusing to download: docs/09-dpia.md does not say "
            "**R5-encryption-at-rest: CONFIRMED** (gate R5).\n"
            "The adopted DPIA relies on encryption at rest to hold R5's residual severity "
            "down. Enable full-disk encryption, then set that flag in the same change.",
            file=sys.stderr,
        )
        return 2

    if not args.upstream.exists():
        print(f"Upstream script not found: {args.upstream}", file=sys.stderr)
        return 2

    # Checked before anything is fetched, and not caught: retrieving while unable to say
    # which objections were in force would mean honouring Article 21 only when someone
    # remembered to look. An empty list is a valid answer; a missing one is not.
    try:
        exclusions.load()
    except exclusions.ExclusionListMissing as error:
        print(f"Refusing to download: {error}", file=sys.stderr)
        return 2

    # argparse.REMAINDER keeps the "--" that separates our flags from the upstream
    # script's, and upstream's own argparse then rejects it as an unrecognised argument.
    # The failure is quiet in the worst way: the wrapper still writes a retrieval record
    # describing a run that downloaded nothing.
    passthrough = args.upstream_args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    command = upstream_command(args.upstream, args.out_dir, passthrough)
    completed = subprocess.run(command, check=False)
    record = write_retrieval_record(args.out_dir, command, completed.returncode)
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
