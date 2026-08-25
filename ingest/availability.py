"""Record whether each sampled ``.ulg`` was actually retrievable. Closes audit row A8.

Dronecode announced a 12-month, retroactive retention policy for uploaded logs on
2024-10-14. The metadata dump still describes logs from 2016, so metadata plainly
outlives *something*; whether it outlives the file is what decides whether the H1 frame
is 79,477 runs or 28,402.

[ADR-0012] decided to measure that here rather than wait for a forum reply, and to do it
as a byproduct: every sampled log either downloads or it does not, so availability falls
out of requests the analysis already makes. There is no separate probe, which matters
because ``robots.txt`` disallows every path and a survey crawl would still have been a
crawl.

**A file on disk is not availability.** A service can answer a request for a deleted
object with a 200 and an error page, and a downloader that only checks status codes
would record that as present. So presence is judged on the ULog magic bytes, not on the
file existing -- ``ULog\\x01\\x12\\x35``, the format's own header.

    uv run python -m ingest.availability
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from analysis.common import exclusions
from analysis.common.manifest import add_output, build_manifest, write_manifest

# The ULog header: 'ULog' then the format's magic bytes. Checked instead of trusting
# either the file's existence or the downloader's exit code.
ULOG_MAGIC = b"ULog\x01\x12\x35"
MIN_PLAUSIBLE_BYTES = 4096


def is_a_real_ulog(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_PLAUSIBLE_BYTES:
        return False
    with path.open("rb") as handle:
        return handle.read(len(ULOG_MAGIC)) == ULOG_MAGIC


def assess(sample: list[dict[str, Any]], raw_dir: Path) -> tuple[list[dict[str, Any]], dict]:
    """Fill ``ulg_available`` per row and summarise by stratum."""
    by_stratum: dict[str, dict[str, int]] = defaultdict(lambda: {"requested": 0, "available": 0})
    oldest_available = None
    for row in sample:
        available = is_a_real_ulog(raw_dir / f"{row['log_id']}.ulg")
        row["ulg_available"] = available
        cell = by_stratum[row["stratum"]]
        cell["requested"] += 1
        if available:
            cell["available"] += 1
            date = (row.get("log_date") or "")[:10]
            if date and (oldest_available is None or date < oldest_available):
                oldest_available = date

    requested = sum(c["requested"] for c in by_stratum.values())
    available = sum(c["available"] for c in by_stratum.values())
    return sample, {
        "requested": requested,
        "available": available,
        "missing": requested - available,
        "availability_rate": round(available / requested, 4) if requested else None,
        "oldest_available_log_date": oldest_available,
        "by_stratum": {k: dict(v) for k, v in sorted(by_stratum.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=Path, default=Path("data/pilot-sample.jsonl"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/pilot-availability.json"))
    args = parser.parse_args(argv)

    manifest = build_manifest(
        name="px4-pilot-availability",
        hypothesis="none",
        entrypoint="ingest/availability.py",
        description="Whether each sampled .ulg was retrievable, by stratum. Audit row A8, "
        "measured as a byproduct of the pilot retrieval rather than by a separate probe.",
        parameters={
            "ulog_magic_checked": True,
            "min_plausible_bytes": MIN_PLAUSIBLE_BYTES,
            "exclusions": exclusions.load().state(),
        },
    )

    rows = [
        json.loads(line)
        for line in args.sample.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows, summary = assess(rows, args.raw)

    args.sample.write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")

    add_output(manifest, args.out)
    path = write_manifest(manifest)
    print(json.dumps(summary, indent=2))
    print(f"manifest: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
