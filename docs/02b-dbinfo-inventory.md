# 02b — What the public PX4 metadata actually contains

Computed from one retrieval of `https://cdn.logs.px4.io/dbinfo.json` on **2026-08-20**
(gzip 30.7 MB, 356 MB decompressed, regenerated daily). No logs were downloaded.

This is most of what M2 was budgeted a week to discover, and it cost one request.

**Reproduce:** `uv run python -m ingest.dbinfo_audit`. Every number below comes from
[`../ingest/dbinfo_audit.py`](../ingest/dbinfo_audit.py), with results in
`artifacts/dbinfo-audit.json` and manifest `artifacts/manifests/{mid}.json`
recording the content hash of the exact dump used. The dump is regenerated daily, so
a later run is a different sampling frame and will not reproduce these figures — which
is what the manifest is for.

## Shape

**450,395 public logs.** All 26 fields are present on every record:

```
log_id  log_date  description  feedback  type  wind_speed  rating  video_url
error_labels  source  duration_s  mav_type  estimator  sys_autostart_id  sys_hw
ver_sw  ver_sw_release  num_logged_errors  num_logged_warnings  flight_modes
vehicle_uuid  flight_mode_durations  vehicle_name  airframe_name  airframe_type
download_url
```

**There are no coordinates.** Position exists only inside the `.ulg`. Every
geography-dependent question — which is all of H1 — requires downloading logs.

## Population

| | count | share |
|---|---|---|
| Total public logs | 450,395 | |
| `sys_hw == PX4_SITL` | 33,762 | 7.5 % |
| Real hardware | 416,633 | 92.5 % |

SITL is identifiable from metadata alone, so the control-population split costs
nothing. Real-hardware flight time totals **24,924 hours** (25 records with
implausible `duration_s` dropped).

## The duration problem

| statistic | value |
|---|---|
| median | **79 s** |
| p90 | 520 s |
| p99 | 2,059 s |
| logs ≥ 120 s | 161,243 |
| logs ≥ 300 s | 79,477 |

Most public logs are bench runs and short hops. The usable population is bounded by
the ≥ 300 s tier — **79,477 logs before any other filter**, not 450,395. This is the
single most important number for gate G2 and it was previously unknown.

**300 s is provisional and is not an ERA5 property.** A reanalysis supplies a
background field for a two-minute flight as readily as for a twenty-minute one. What
a short log fails to supply is the other side of the comparison: enough post-takeoff
flight for the EKF wind state to converge, enough movement to excite it, and enough
samples clear of transients. Where that boundary really falls is a question about the
estimator, answerable only against real logs. It may land at 180 s or at 600 s; the
threshold is a manifest parameter so the versions can be compared.

## Airframes (real hardware)

Fixed-wing and VTOL together: **60,079**. Fixed Wing 26,289 · VTOL Standard 24,707 ·
Tiltrotor VTOL 10,545 · tailsitters ~6,809. Multirotor and helicopter: 346,742.

Since H1's fallback under a failed estimator-config check is "narrow to fixed-wing
with airspeed", 60k is the headroom for that fallback — comfortable.

`estimator` is `EKF2` on 446,969 logs (99.2 %). The remainder are Q, LPE and INAV.

## A declared wind field already exists

`wind_speed` is set by the uploader on the web form and encodes
`{0: Calm, 5: Breeze, 8: Gale, 10: Storm}`; `-1` means not given.

| value | logs |
|---|---|
| −1 (not given) | 427,068 |
| Calm | 18,348 |
| Breeze | 4,107 |
| Gale | 470 |
| Storm | 402 |

**23,327 logs (5.2 %) carry a human-declared wind category** — coarse, subjective,
and entirely independent of both ERA5 and EKF2. It is a cheaper third source than
METAR and it needs no proximity to an airport. Only 1,113 of them are real-hardware
fixed-wing or VTOL, so it strengthens rather than replaces the METAR subset.

## Labels that already exist

`error_labels` uses a fixed vocabulary of eight: Other, Vibration, Airframe-design,
Sensor-error, Component-failure, Software, Human-error, **External-conditions**.
Usage is sparse — External-conditions appears on 160 logs; the largest, Vibration, on
478. `rating` is richer: good 18,328 · great 2,903 · unsatisfactory 1,020 ·
crash_sw_hw 401 · crash_pilot 188.

Sparse, but free, human-applied, and already an ontology — consistent with not
building one.

## Consequences

1. M2's sample audit is largely already done, on the full population rather than
   ~10² logs. Its remaining content is the part that needs the `.ulg`: field
   coverage, estimator configuration, and geography.
2. Download budget should be spent on a **stratified sample of the ≥ 300 s,
   non-SITL tier**, drawn using these metadata as the sampling frame.
3. `wind_speed` gives an independent third source for H1 at zero retrieval cost.
