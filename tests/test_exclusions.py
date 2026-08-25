"""An objection that the code cannot see is an objection that was not honoured.

Every test here is about a way the mechanism could quietly fail open: a missing list
read as an empty one, a malformed line skipped, a vehicle-level objection honoured only
for the logs that existed when it arrived, or the list itself leaking into a manifest.

The identifiers are synthetic and describe no real person or airframe.
"""

from __future__ import annotations

import json

import pytest

from analysis.common import exclusions as ex

VEHICLE = "11111111-2222-3333-4444-555555555555"
LOG = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def write(path, entries):
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8", newline="\n")
    return path


def test_a_missing_list_is_fatal_not_empty(tmp_path) -> None:
    """ "Nobody objected" and "I did not check" must not be the same state."""
    with pytest.raises(ex.ExclusionListMissing, match="does not exist"):
        ex.load(tmp_path / "absent.jsonl")


def test_an_empty_list_is_a_valid_declaration(tmp_path) -> None:
    """Declaring zero objections is cheap, so absence has no excuse to mean it."""
    path = tmp_path / "exclusions.jsonl"
    path.write_text("", encoding="utf-8")
    loaded = ex.load(path)
    assert loaded.count == 0
    assert loaded.excludes(log_id=LOG, vehicle_uuid=VEHICLE) is False


def test_a_malformed_line_is_fatal(tmp_path) -> None:
    """Skipping it would drop precisely the record that must not be dropped."""
    path = tmp_path / "exclusions.jsonl"
    path.write_text('{"kind": "vehicle_uuid", "value": "x"}\nnot json\n', encoding="utf-8")
    with pytest.raises(ex.ExclusionListInvalid, match="not JSON"):
        ex.load(path)


@pytest.mark.parametrize(
    "entry",
    [
        {"kind": "uuid", "value": VEHICLE},  # not one of the two accepted kinds
        {"kind": "vehicle_uuid", "value": ""},
        {"kind": "vehicle_uuid"},
        {"value": VEHICLE},
    ],
)
def test_an_unusable_entry_is_fatal(tmp_path, entry) -> None:
    path = write(tmp_path / "exclusions.jsonl", [entry])
    with pytest.raises(ex.ExclusionListInvalid):
        ex.load(path)


def test_a_vehicle_objection_covers_logs_it_never_named(tmp_path) -> None:
    """The promise is that later runs do not re-include -- including later uploads.

    An objection scoped only to the logs that existed when it arrived would be honoured
    once and then quietly lapse, which is the failure this test exists to prevent.
    """
    path = write(tmp_path / "exclusions.jsonl", [{"kind": "vehicle_uuid", "value": VEHICLE}])
    loaded = ex.load(path)
    assert loaded.excludes(vehicle_uuid=VEHICLE, log_id="a-log-uploaded-next-year") is True


def test_a_log_objection_does_not_exclude_the_whole_vehicle(tmp_path) -> None:
    """Scope runs the way it was asked for, not wider: over-excluding is also a wrong."""
    path = write(tmp_path / "exclusions.jsonl", [{"kind": "log_id", "value": LOG}])
    loaded = ex.load(path)
    assert loaded.excludes(log_id=LOG) is True
    assert loaded.excludes(vehicle_uuid=VEHICLE, log_id="another-log") is False


def test_state_records_which_exclusions_applied_and_never_whose(tmp_path) -> None:
    """The manifest needs to identify the list in force. It must not carry its contents.

    Publishing the list would announce which operators exercised a right -- a more
    revealing disclosure than the flight data the objection was about.
    """
    path = write(
        tmp_path / "exclusions.jsonl",
        [
            {"kind": "vehicle_uuid", "value": VEHICLE, "received": "2026-09-01"},
            {"kind": "log_id", "value": LOG, "received": "2026-09-03"},
        ],
    )
    state = ex.load(path).state()
    assert state["count"] == 2
    assert state["latest_received"] == "2026-09-03"
    assert state["digest"].startswith("sha256:")
    serialised = json.dumps(state)
    assert VEHICLE not in serialised
    assert LOG not in serialised


def test_the_digest_moves_when_the_list_does(tmp_path) -> None:
    """Two runs under different exclusion states must be distinguishable afterwards."""
    path = tmp_path / "exclusions.jsonl"
    first = ex.load(write(path, [{"kind": "log_id", "value": LOG}])).digest
    second = ex.load(
        write(path, [{"kind": "log_id", "value": LOG}, {"kind": "log_id", "value": "z"}])
    ).digest
    assert first != second


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (LOG, LOG),
        (f"https://cdn.logs.px4.io/{LOG}.ulg", LOG),
        (f"https://review.px4.io/plot_app?log_id={LOG}", LOG),
        (f"https://logs.px4.io/plot_app?log_id={LOG}&other=1", LOG),
        (f"  {LOG}  ", LOG),
    ],
)
def test_an_objector_may_send_a_link_instead_of_an_id(reference, expected) -> None:
    """PRIVACY.md invites a link, so accepting one is part of the promise, not a nicety.

    Requiring a person exercising a right to dig out an internal identifier is a way of
    making the right harder to use.
    """
    assert ex.log_id_from(reference) == expected
