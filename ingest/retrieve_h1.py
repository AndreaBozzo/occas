"""Retrieve the H1 draw: download in chunks, convert, prune, and record what arrived.

This drives ``ingest/px4_download.py`` and ``ingest/convert.sh`` rather than replacing
either. Both gates (G1, R5) and the Article 21 exclusion check stay where they are, in
the download wrapper, and are re-checked on every chunk -- an objection received during
a four-hour retrieval takes effect on the next chunk rather than after the whole run.

    uv run python -m ingest.retrieve_h1                      # start, or resume
    uv run python -m ingest.retrieve_h1 --dry-run            # plan only, no requests

**Why chunks.** 1,600 log ids on one command line is about 59,000 characters and Windows
refuses anything over 32,767. This is a platform limit, not a preference: the pilot's 100
ids fitted in 3,832 characters and hid it.

**Why the frame is served locally.** ``download_logs.py`` fetches the whole ``dbinfo``
dump on every invocation and filters it by ``--log-id``. That dump is 30 MB gzipped, so
sixteen chunks would pull roughly half a gigabyte from the maintainers' CDN to re-derive
a file already on disk -- and it would be a *different* file, fetched today, while the
draw was made from the copy pinned on 2026-08-20 (A6, adr/0012). A log deleted upstream
since then would silently fail to match the filter, and be indistinguishable from one
that was never requested. So the pinned dump is served over loopback, and every id is
checked against it before the first request. After that, an id that does not arrive is a
retrieval failure and nothing else -- which is what audit row A8 is measuring.

**Why availability is observed here.** ``convert.sh`` deletes each ``.ulg`` once its
conversion has produced Parquet (DPIA 1.4, R5). Availability therefore cannot be measured
from ``data/raw`` afterwards, because by then the successful cases are the ones that are
gone. Each chunk is observed before it is pruned and the observation written into the
sample. A run already converted is recorded available without re-checking a file that no
longer exists: Parquet on disk is proof the ULog was real, which the file's presence
never was.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from analysis.common import exclusions
from analysis.common.manifest import add_output, build_manifest, write_manifest
from ingest.availability import MIN_PLAUSIBLE_BYTES, is_a_real_ulog, summarise

REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = REPO_ROOT / "data" / "upstream" / "download_logs.py"
DBINFO = REPO_ROOT / "data" / "dbinfo.json.gz"
CONVERT = REPO_ROOT / "ingest" / "convert.sh"

# The maintainers' own documented floor: 10 requests/minute (adr/0012). Not a tunable.
DELAY_SECONDS = 6


class _PinnedDbInfo(BaseHTTPRequestHandler):
    """Serves the pinned dbinfo dump, and nothing else, on loopback."""

    payload = b""

    def do_GET(self) -> None:  # noqa: N802  (http.server's spelling)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *args: Any) -> None:
        """Silence per-request logging; the retrieval log is about logs, not HTTP."""


def serve_pinned_frame() -> tuple[HTTPServer, str, set[str]]:
    """Serve ``data/dbinfo.json.gz`` decompressed on an ephemeral loopback port.

    The parsed entries are reduced to a set of ids and then dropped: the dump is 450,000
    records and holding them as Python objects for the hours a retrieval takes costs
    gigabytes, while the only question asked of them is whether an id is in the frame.
    Ids are compared without dashes, as upstream's own filter compares them.
    """
    payload = gzip.decompress(DBINFO.read_bytes())
    in_frame = {entry["log_id"].replace("-", "") for entry in json.loads(payload)}
    _PinnedDbInfo.payload = payload
    server = HTTPServer(("127.0.0.1", 0), _PinnedDbInfo)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address[0], server.server_address[1]
    return server, f"http://{host}:{port}/dbinfo", in_frame


def read_sample(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_sample(path: Path, rows: list[dict[str, Any]]) -> None:
    """Rewrite the sample atomically: an interrupted retrieval must not truncate it."""
    body = "".join(json.dumps(r) + "\n" for r in rows)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(body, encoding="utf-8", newline="\n")
    temp.replace(path)


def has_parquet(parquet_dir: Path, log_id: str) -> bool:
    """True once conversion has produced at least one Parquet file for this run.

    The same bar convert.sh uses before deleting a ``.ulg``, and for the same reason:
    ulog-convert reports success, and creates an output directory, for a file that is
    not a ULog at all.
    """
    return any((parquet_dir / log_id).glob("*.parquet"))


def plan(
    rows: list[dict[str, Any]], raw: Path, parquet: Path
) -> tuple[list[dict[str, Any]], int, int]:
    """Mark what is already in hand, and return the rows still to request.

    Resumable, and prune-proof: a converted run is settled even though its ``.ulg`` was
    deleted, so a resumed retrieval does not re-request the corpus it already holds.
    """
    converted = downloaded = 0
    pending = []
    for row in rows:
        if has_parquet(parquet, row["log_id"]):
            row["ulg_available"] = True
            converted += 1
        elif is_a_real_ulog(raw / f"{row['log_id']}.ulg"):
            row["ulg_available"] = True
            downloaded += 1
        else:
            pending.append(row)
    return pending, converted, downloaded


def download_chunk(chunk: list[dict[str, Any]], raw: Path, db_info_api: str) -> int:
    """One call to the download wrapper, which re-checks both gates before fetching."""
    ids = [row["log_id"] for row in chunk]
    command = [
        sys.executable,
        "-m",
        "ingest.px4_download",
        "--out-dir",
        str(raw),
        "--upstream",
        str(UPSTREAM),
        "--",
        "--log-id",
        *ids,
        "--max-num",
        str(len(ids)),
        "--yes",
        "--delay",
        str(DELAY_SECONDS),
        "--db-info-api",
        db_info_api,
    ]
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def for_bash(path: Path) -> str:
    """A path bash will accept, relative to the repo root.

    ``str(Path)`` on Windows produces ``C:\\dev\\occas\\ingest\\convert.sh``, and bash
    reads every backslash as an escape: the first smoke test invoked
    ``C:devoccasingestconvert.sh``, which does not exist. It printed that on stderr,
    the return code was ignored, and the run reported success having converted nothing.
    Relative to the repo root the paths are also the ones the pilot's conversion records
    already contain, so ``conversion-results.jsonl`` stays consistent across batches.
    """
    return Path(os.path.relpath(path, REPO_ROOT)).as_posix()


def find_bash() -> str:
    """The absolute path to a bash that can see this repo and the tools installed for it.

    Not the string ``"bash"``. Windows' CreateProcess searches ``System32`` before it
    searches ``PATH``, and ``System32\\bash.exe`` is the WSL launcher -- so a bare
    ``bash`` here started WSL, which reported ``Linux ... microsoft-standard-WSL2``,
    saw the repo as ``/mnt/c/dev/occas``, and had no ``ulog-convert`` on its PATH. The
    conversion failed for a reason that had nothing to do with conversion.
    ``shutil.which`` searches ``PATH`` only, which is the search we actually want, and
    anything under the Windows directory is rejected outright because that is where the
    launcher lives. ``BASH`` overrides both.
    """
    override = os.environ.get("BASH")
    if override:
        return override
    system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        found = shutil.which("bash", path=directory)
        if found and not Path(found).is_relative_to(system_root):
            return found
    raise FileNotFoundError(
        "No bash found outside the Windows directory. Git Bash ships one; set BASH to "
        "its path if it is installed somewhere this search does not reach."
    )


def convert_chunk(raw: Path, parquet: Path) -> int:
    """Convert what is in ``raw`` and delete the ``.ulg`` files that produced Parquet."""
    return subprocess.run(
        [find_bash(), for_bash(CONVERT), for_bash(raw), for_bash(parquet)],
        cwd=REPO_ROOT,
        check=False,
        env={**os.environ, "PRUNE_RAW": "1"},
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=Path, default=REPO_ROOT / "data" / "h1-sample.jsonl")
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--parquet", type=Path, default=REPO_ROOT / "data" / "parquet")
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "artifacts" / "h1-availability.json"
    )
    parser.add_argument(
        "--progress", type=Path, default=REPO_ROOT / "data" / "h1-retrieval-progress.jsonl"
    )
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; make no requests.")
    args = parser.parse_args(argv)

    rows = read_sample(args.sample)
    server, db_info_api, in_frame = serve_pinned_frame()
    try:
        # Every drawn id must be in the frame it was drawn from. If it is not, upstream's
        # filter drops it silently and the miss is indistinguishable from a deleted log.
        missing = [r["log_id"] for r in rows if r["log_id"].replace("-", "") not in in_frame]
        if missing:
            print(
                f"Refusing to retrieve: {len(missing)} drawn ids are absent from the pinned "
                f"frame ({DBINFO}), starting with {missing[0]}. The draw and the frame "
                "disagree; re-draw rather than retrieve a different set.",
                file=sys.stderr,
            )
            return 2

        pending, converted, downloaded = plan(rows, args.raw, args.parquet)
        write_sample(args.sample, rows)
        chunks = [pending[i : i + args.chunk_size] for i in range(0, len(pending), args.chunk_size)]
        hours = len(pending) * DELAY_SECONDS / 3600
        print(
            f"Frame {len(in_frame)} logs (pinned, served at {db_info_api}).\n"
            f"Drawn {len(rows)}: {converted} already converted, {downloaded} already "
            f"downloaded, {len(pending)} to retrieve in {len(chunks)} chunks.\n"
            f"At {DELAY_SECONDS}s between requests that is {hours:.1f} h of delay alone.",
            flush=True,
        )
        if args.dry_run:
            return 0

        # Built before the first request, not after the last: retrieval and environment
        # metadata cannot be reconstructed afterwards (adr/0004). The frame is an input
        # because it is pinned and hashable; the sample file is not, because this run
        # rewrites it as observations come in.
        manifest = build_manifest(
            name="px4-h1-retrieval",
            hypothesis="H1",
            entrypoint="ingest/retrieve_h1.py",
            inputs=[DBINFO, REPO_ROOT / "artifacts" / "h1-sample-summary.json"],
            description="Chunked retrieval of the H1 draw from PX4 Flight Review, with "
            "per-chunk conversion, pruning of the raw logs, and availability observed "
            "before each prune.",
            parameters={
                "chunk_size": args.chunk_size,
                "delay_seconds": DELAY_SECONDS,
                "drawn": len(rows),
                "requested": len(pending),
                "already_held": converted + downloaded,
                "frame_entries": len(in_frame),
                "frame_served_locally": True,
                "prune_raw": True,
                "ulog_magic_checked": True,
                "min_plausible_bytes": MIN_PLAUSIBLE_BYTES,
                "exclusions": exclusions.load().state(),
            },
        )

        args.progress.parent.mkdir(parents=True, exist_ok=True)
        for number, chunk in enumerate(chunks, start=1):
            print(f"\n=== chunk {number}/{len(chunks)} ({len(chunk)} logs) ===", flush=True)
            code = download_chunk(chunk, args.raw, db_info_api)
            if code != 0:
                # download_logs.py exits 1 on HTTP 403/444 -- the IP is blocked. Carrying
                # on would turn one refusal into fifteen hundred more requests, so this
                # stops here and keeps what has already been retrieved and converted.
                print(
                    f"Retrieval stopped: the download wrapper exited {code} on chunk "
                    f"{number}. Nothing further is requested. Re-run to resume once the "
                    "cause is understood -- work already converted is not repeated.",
                    file=sys.stderr,
                )
                return code

            # Observed before the prune, because the prune deletes exactly the successes.
            observed_at = datetime.now(UTC).isoformat()
            arrived = 0
            with args.progress.open("a", encoding="utf-8", newline="\n") as handle:
                for row in chunk:
                    path = args.raw / f"{row['log_id']}.ulg"
                    available = is_a_real_ulog(path)
                    row["ulg_available"] = available
                    arrived += available
                    handle.write(
                        json.dumps(
                            {
                                "log_id": row["log_id"],
                                "chunk": number,
                                "ulg_available": available,
                                "bytes": path.stat().st_size if path.exists() else 0,
                                "observed_at": observed_at,
                            }
                        )
                        + "\n"
                    )
            write_sample(args.sample, rows)
            print(f"Chunk {number}: {arrived}/{len(chunk)} arrived as real ULogs.", flush=True)

            if arrived == 0:
                # Not a slow chunk: a hundred consecutive misses is a block, or a frame
                # that no longer contains the draw. Either way the next hundred requests
                # will not help.
                print(
                    f"Retrieval stopped: no log in chunk {number} arrived. That is a "
                    "block or a frame mismatch, not bad luck.",
                    file=sys.stderr,
                )
                return 1

            # Checked, not fired and forgotten. convert.sh exits non-zero only when the
            # batch produced no results at all; carrying on from that would mean
            # downloading the rest of the draw into a data/raw nothing is emptying.
            code = convert_chunk(args.raw, args.parquet)
            if code != 0:
                print(
                    f"Retrieval stopped: conversion of chunk {number} produced nothing "
                    f"(exit {code}). The logs are retrieved and not pruned; fix the "
                    "conversion and re-run to resume.",
                    file=sys.stderr,
                )
                return code

            if number < len(chunks):
                time.sleep(DELAY_SECONDS)

        summary = summarise(rows)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
        add_output(manifest, args.out)
        path = write_manifest(manifest)
        print(json.dumps(summary, indent=2))
        print(f"\nAvailability: {args.out}\nmanifest: {path}")
        return 0
    finally:
        server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
