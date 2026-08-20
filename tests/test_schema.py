"""The schemas compile, the valid fixtures pass, and the invalid ones fail for the
reason they were written to fail for.

A validator that never rejects anything guards nothing, so each negative fixture
declares the JSON pointer where it is expected to break, and the test asserts the
error lands there. Otherwise a fixture rejected for an unrelated reason -- a stray
key, a typo -- would look like coverage it does not provide.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from analysis.common.schema import SCHEMA_DIR, load, schema_paths, validate, validator_for

FIXTURES = Path(__file__).parent / "fixtures" / "records"
META_KEYS = ("_why_invalid", "_schema", "_error_path")


def _strip_meta(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in META_KEYS}


@pytest.mark.parametrize("path", schema_paths(), ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(path: Path) -> None:
    Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", schema_paths(), ids=lambda p: p.name)
def test_schema_has_id_title_and_description(path: Path) -> None:
    schema = load(path.name)
    assert schema.get("$id"), f"{path.name} has no $id, so nothing can reference it"
    assert schema.get("title"), f"{path.name} has no title"
    assert schema.get("description"), f"{path.name} has no description"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_valid_fixture_matches_its_schema(path: Path) -> None:
    """Fixture file names mirror schema file names."""
    schema_name = f"{path.stem}.json"
    assert (SCHEMA_DIR / schema_name).exists(), f"no schema named {schema_name}"
    validate(json.loads(path.read_text(encoding="utf-8")), schema_name)


@pytest.mark.parametrize(
    "path", sorted((FIXTURES / "invalid").glob("*.json")), ids=lambda p: p.stem
)
def test_invalid_fixture_fails_at_the_declared_path(path: Path) -> None:
    record = json.loads(path.read_text(encoding="utf-8"))
    schema_name = record["_schema"]
    expected = record["_error_path"]
    stripped = _strip_meta(record)

    errors = list(validator_for(schema_name).iter_errors(stripped))
    assert errors, f"{path.name} was expected to be rejected by {schema_name}"

    observed = {".".join(str(p) for p in e.absolute_path) for e in errors}
    assert expected in observed, (
        f"{path.name} was rejected, but at {sorted(observed)} rather than at "
        f"{expected!r} -- the fixture is not testing what it claims to test"
    )


def test_cross_schema_reference_resolves() -> None:
    """``$ref: source_metadata.json`` resolves against the referring schema's ``$id``.

    Fails loudly if a schema stops being registered, or loses its ``$id``.
    """
    run = json.loads((FIXTURES / "run.json").read_text(encoding="utf-8"))
    run["source"]["retrieved_at"] = 12345  # wrong type, inside the referenced schema
    with pytest.raises(ValidationError) as excinfo:
        validate(run, "run.json")
    assert list(excinfo.value.absolute_path)[:2] == ["source", "retrieved_at"]


def test_odd_taxonomy_is_not_written_yet() -> None:
    """Blocked on the M0 prior-art check (docs/03-odd-representation.md).

    Delete this test in the same commit that records the check and writes the taxonomy.
    """
    doc = (SCHEMA_DIR.parent / "docs" / "03-odd-representation.md").read_text(encoding="utf-8")
    if "unresolved" not in doc:
        pytest.skip("prior-art check complete; the taxonomy may now exist")
    assert not (SCHEMA_DIR / "odd_taxonomy.yaml").exists(), (
        "schemas/odd_taxonomy.yaml exists while docs/03-odd-representation.md still "
        "has unresolved prior-art rows (JARUS)"
    )
