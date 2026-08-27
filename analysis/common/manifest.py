"""Build and write ``AnalysisManifest`` records.

No result without a manifest (``docs/adr/0004``). Retrieval and environment metadata
are captured *when the analysis runs*, because they cannot be reconstructed later: the
ERA5T product may have been superseded, and the installed tool version today is not
necessarily the one that produced the numbers.

The schema is ``schemas/analysis_manifest.json``; this module is only a convenient way
to produce records that satisfy it, and ``write_manifest`` validates before writing.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "artifacts" / "manifests"

_HASH_CHUNK = 1 << 20


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    """Return an algorithm-prefixed hash of a file's bytes, read in binary.

    The hash is over bytes as they sit on disk, so anything whose hash is recorded has
    to be written with ``newline="\\n"``: ``write_text`` translates on Windows,
    ``.gitattributes`` checks the file back out as LF, and the recorded hash then
    reproduces for nobody who clones the repository. ``tests/test_manifest.py`` holds
    that line against the committed artifacts rather than against a temporary file.
    """
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return f"{algorithm}:{digest.hexdigest()}"


def git_state(repo: Path = REPO_ROOT) -> tuple[str, bool]:
    """Return ``(commit, dirty)`` for the repository.

    A dirty tree is recorded rather than rejected: exploratory runs are legitimate,
    publication from a dirty manifest is not. The distinction is enforced by
    ``require_publishable``, not here.
    """
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", True
    return commit, bool(status)


def dependency_versions(distributions: Iterable[str] | None = None) -> dict[str, str]:
    """Resolved versions of the declared dependencies, as actually installed."""
    if distributions is None:
        requires = metadata.requires("operational-context-corpus") or []
        distributions = {
            r.split(";")[0].split("[")[0].split("<")[0].split(">")[0].split("=")[0].strip()
            for r in requires
        }
    versions: dict[str, str] = {}
    for name in sorted(n for n in distributions if n):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def build_manifest(
    *,
    name: str,
    hypothesis: str,
    entrypoint: str,
    inputs: Iterable[Path | Mapping[str, Any]] = (),
    parameters: Mapping[str, Any] | None = None,
    seed: int | None = None,
    external_tools: Iterable[Mapping[str, str]] = (),
    description: str | None = None,
) -> dict[str, Any]:
    """Assemble a manifest record. Inputs may be paths or pre-built input mappings.

    **Call this before the outputs are written.** It captures ``git_state``, which reads
    ``git status`` over the whole tree; an output that is tracked in git dirties that
    tree the moment it is rewritten. Built afterwards, a manifest reports ``dirty: true``
    for every run that changed its own result, and ``require_publishable`` can never
    pass. ``code.dirty`` is about the state of the code that ran, not about the result
    it has just produced.
    """
    commit, dirty = git_state()
    resolved_inputs: list[dict[str, Any]] = []
    for item in inputs:
        if isinstance(item, Mapping):
            resolved_inputs.append(dict(item))
        else:
            path = Path(item)
            resolved_inputs.append(
                {
                    "path": path.as_posix(),
                    "content_hash": hash_file(path),
                }
            )
    return {
        "manifest_id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "analysis": {"name": name, "hypothesis": hypothesis, "description": description},
        "code": {"entrypoint": entrypoint, "git_commit": commit, "dirty": dirty},
        "inputs": resolved_inputs,
        "external_tools": [dict(t) for t in external_tools],
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "dependencies": dependency_versions(),
        },
        "parameters": dict(parameters or {}),
        "seed": seed,
        "outputs": [],
    }


def add_output(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    """Record a produced file and its hash. Call after the file is written.

    The path is recorded relative to the repository root whenever the file sits inside
    it. An absolute path identifies the artifact for one checkout and for no other, so a
    reader of a clone cannot resolve it and a test looking for it can only skip what it
    does not find. Two manifests written before this rule record an absolute path; the
    hash beside it is unaffected, and it is the hash that attests the artifact.
    """
    resolved = Path(path).resolve()
    try:
        recorded = resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        recorded = resolved.as_posix()
    manifest["outputs"].append({"path": recorded, "content_hash": hash_file(resolved)})
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    """Raise ``jsonschema.ValidationError`` if the manifest does not satisfy the schema."""
    from analysis.common.schema import validate

    validate(manifest, "analysis_manifest.json")


def require_publishable(manifest: Mapping[str, Any]) -> None:
    """Raise if the manifest describes a run that must not produce published numbers."""
    code = manifest["code"]
    if code["dirty"] or code["git_commit"] == "unknown":
        raise ValueError(
            "Manifest is not publishable: the working tree was dirty or the commit is "
            "unknown, so the result cannot be regenerated from a known state."
        )


def write_manifest(manifest: Mapping[str, Any], directory: Path = MANIFEST_DIR) -> Path:
    """Validate and write a manifest, returning its path."""
    validate_manifest(manifest)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{manifest['manifest_id']}.json"
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return path
