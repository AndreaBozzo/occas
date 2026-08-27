"""No result without a manifest, so the manifest builder is itself tested."""

from __future__ import annotations

import hashlib
import json

import pytest
from jsonschema import ValidationError

from analysis.common import manifest as m


def test_hash_file_matches_hashlib(tmp_path) -> None:
    payload = b"binary\x00bytes\r\n"  # read as bytes: no newline translation
    path = tmp_path / "input.bin"
    path.write_bytes(payload)
    assert m.hash_file(path) == f"sha256:{hashlib.sha256(payload).hexdigest()}"


def test_build_manifest_satisfies_the_schema(tmp_path) -> None:
    inp = tmp_path / "input.parquet"
    inp.write_bytes(b"not really parquet")
    built = m.build_manifest(
        name="h1-agreement-smoke",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/run.py",
        inputs=[inp],
        parameters={"spatial_tolerance_km": 20.0},
        seed=20260820,
        external_tools=[{"name": "ulog-convert", "version": "fixture"}],
    )
    m.validate_manifest(built)
    assert built["inputs"][0]["content_hash"].startswith("sha256:")
    assert built["environment"]["dependencies"], "dependency versions must be resolved"


def test_manifest_rejects_an_unknown_hypothesis() -> None:
    built = m.build_manifest(name="x", hypothesis="H9", entrypoint="x.py")
    with pytest.raises(ValidationError):
        m.validate_manifest(built)


def test_add_output_records_the_hash(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    out = tmp_path / "result.json"
    out.write_text("{}", encoding="utf-8")
    m.add_output(built, out)
    assert built["outputs"][0]["content_hash"] == m.hash_file(out)
    m.validate_manifest(built)


def test_require_publishable_rejects_a_dirty_tree() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "abc123", "dirty": True}
    with pytest.raises(ValueError, match="not publishable"):
        m.require_publishable(built)


def test_require_publishable_rejects_an_unknown_commit() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "unknown", "dirty": False}
    with pytest.raises(ValueError, match="not publishable"):
        m.require_publishable(built)


def test_require_publishable_accepts_a_clean_tree() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "abc123", "dirty": False}
    m.require_publishable(built)


def test_write_manifest_validates_before_writing(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="H9", entrypoint="x.py")
    with pytest.raises(ValidationError):
        m.write_manifest(built, directory=tmp_path)
    assert not list(tmp_path.iterdir()), "an invalid manifest must leave nothing behind"


def test_write_manifest_round_trips(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="H1", entrypoint="x.py")
    path = m.write_manifest(built, directory=tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["manifest_id"] == built["manifest_id"]


def test_write_manifest_writes_lf_only(tmp_path) -> None:
    """Hashes are over bytes, so the writer must not emit CRLF on Windows.

    ``write_text`` translates ``\n`` to ``\r\n`` on Windows unless told otherwise,
    while ``.gitattributes`` stores and checks out LF. A manifest written with CRLF
    therefore records a hash that nobody who clones the repository can reproduce.
    """
    path = m.write_manifest(
        m.build_manifest(name="x", hypothesis="H1", entrypoint="x.py"), tmp_path
    )
    assert b"\r\n" not in path.read_bytes()


def test_every_artifact_in_the_repository_is_attested_by_a_manifest() -> None:
    """The provenance chain must close against the repository, not against a temp file.

    Each artifact in the tree must be re-hashable to the hash some manifest recorded
    for it, which in CI is the committed content. *Some*, not all: a superseded
    manifest legitimately attests an earlier version of the same path, and that
    history is kept rather than rewritten.
    What must never happen is an artifact no manifest attests -- which is what a
    newline translated on the way to disk produces.
    """
    attested: dict[str, set[str]] = {}
    for path in sorted(m.MANIFEST_DIR.glob("*.json")):
        for output in json.loads(path.read_text(encoding="utf-8"))["outputs"]:
            attested.setdefault(output["path"], set()).add(output["content_hash"])
    assert attested, "no manifest records an output"

    checked = 0
    for relative, hashes in sorted(attested.items()):
        produced = m.REPO_ROOT / relative
        if not produced.exists():
            continue  # not every output is committed; those that are must be attested
        # Checked first, and separately, because it is the failure this test exists
        # for and the hash comparison alone would miss it on the machine that caused
        # it: a CRLF artifact hashed on Windows matches the CRLF hash recorded beside
        # it. The two only disagree once git has round-tripped the file to LF, which
        # is to say in CI and on everyone else's clone.
        # ".jsonl" does not end with ".json", so the tuple is not redundant: H1 emits
        # its validation artifacts as JSON Lines and they need the same guard.
        if relative.endswith((".json", ".jsonl")):
            assert b"\r\n" not in produced.read_bytes(), (
                f"{relative} contains CRLF; git stores it as LF, so the hash recorded "
                f"for it here will not reproduce from a clean checkout"
            )
        assert m.hash_file(produced) in hashes, (
            f"{relative} is in the tree but no manifest attests its bytes: "
            f"it hashes to {m.hash_file(produced)}, manifests record {sorted(hashes)}"
        )
        checked += 1
    assert checked, "no committed output was actually re-hashed"
