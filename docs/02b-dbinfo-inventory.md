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

**"Every number" is now a test, not a promise.** It was a promise until 2026-08-25 and
two numbers on this page escaped it, one of them wrong; the manifests also recorded
output hashes that nobody cloning the repository could reproduce. Both are fixed and
both are held by `tests/test_manifest.py` and `tests/test_dbinfo_audit.py` —
[ADR-0010](adr/0010-manifests-are-verified-against-the-repository.md).

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

Non-SITL logs surviving each candidate threshold, all four counted in the same pass:

| ≥ 120 s | ≥ 180 s | ≥ 300 s | ≥ 600 s |
|---|---|---|---|
| 161,243 | 120,548 | **79,477** | 33,356 |

Most public logs are bench runs and short hops. The usable population is bounded by
the ≥ 300 s tier — **79,477 logs before any other filter**, not 450,395. This is the
single most important number for gate G2 and it was previously unknown.

The tiers are counted together because the threshold is the thing least settled here:
across the plausible range it moves the frame by a factor of five, and every one of
those frames is a different study. Quoting one of them requires the others to be
visible next to it.

**300 s is provisional and is not an ERA5 property.** A reanalysis supplies a
background field for a two-minute flight as readily as for a twenty-minute one. What
a short log fails to supply is the other side of the comparison: enough post-takeoff
flight for the EKF wind state to converge, enough movement to excite it, and enough
samples clear of transients. Where that boundary really falls is a question about the
estimator, answerable only against real logs. It may land at 180 s or at 600 s; the
threshold is a manifest parameter so the versions can be compared.

## The frame counts metadata, and metadata may outlive the log

Dronecode announced a **12-month retention policy** for uploaded logs on 2024-10-14,
retroactively. This dump still describes records from 2016, so metadata outlives
something — but whether it outlives the `.ulg` is unknown, and it is the difference
between two quite different studies:

| ≥ 300 s, non-SITL | logs |
|---|---|
| logged within 365 days of the dump's newest record (cutoff 2025-08-19) | 28,402 |
| older | 51,075 |

**Only 35.7 % of the frame is inside the retention window.** If the policy is enforced
as announced, the retrievable frame is 28k rather than 79k. That is still ample for a
sample of one to three thousand runs — the loss is not of *n* but of spread, since the
older records carry most of the firmware, airframe and geographic diversity H1
stratifies on.

**Measured on 2026-08-25, and the exposure did not materialise.** The pilot retrieval
drew 50 logs from outside the window and **all 50 downloaded**, with valid ULog headers;
100/100 overall, oldest retrieved **2017-09-18**. Metadata and `.ulg` both outlive the
announced retention. The frame therefore stays at 79,477, and the 28,402 figure above is
what the risk *would* have cost, not what it did.

The rule of three bounds the missing rate outside the window at about 6% at 95%
confidence on 50 draws — high availability rather than a demonstrated 100%, and it is
recomputed if a later sample starts missing files. Audit row
[A8](01-source-audit.md), answered by measurement rather than by a reply
([ADR-0012](adr/0012-no-open-question-waits-for-a-reply.md)).

## Airframes (real hardware)

Every real-hardware log falls into exactly one class, and the three sum to 416,633:

| class | logs |
|---|---|
| Fixed-wing and VTOL | **60,079** |
| Rotorcraft | 346,767 |
| Everything else | 9,787 |

Fixed-wing and VTOL by subtype: Fixed Wing 23,301 · VTOL Standard 21,462 · Tiltrotor
VTOL 9,096 · tailsitters 5,993 · VTOL reserved variants 227.

"Everything else" is mostly `unknown type` (5,397) and ground rovers (2,288), and it
is where the corpus stops being an aircraft corpus: 331 boats, 68 rockets, 67
submarines, 48 free balloons, an airship, two ground installations. Recorded, not
filtered — but nothing outside the first row is a candidate for H1.

**These are real-hardware counts, and an earlier version of this page was not.** It
printed subtypes counted over *all* logs beside a total counted over real hardware
only: the parts summed to 68,350 against a stated 60,079, and even that all-log list
was short, because the distribution was truncated to the top fifteen and the VTOL
variants fell off the end. SITL is the whole of the difference — 8,645 of the 68,724
fixed-wing and VTOL logs are simulated. `mav_type` is now emitted three ways,
`mav_type_all` / `mav_type_real` / `mav_type_sitl`, none of them truncated, so the two
populations cannot be quoted as one again. The rotorcraft figure was also wrong by 25
and was not computed by the script at all; it is now.

Since H1's fallback under a failed estimator-config check is "narrow to fixed-wing
with airspeed", 60k is the headroom for that fallback — comfortable.

`estimator` is `EKF2` on 446,969 logs (99.2 %). The remainder are Q, LPE and INAV.

## A declared wind field already exists

`wind_speed` is set by the uploader on the web form and encodes
`{0: Calm, 5: Breeze, 8: Gale, 10: Storm}`; `-1` means not given.

**The encoding is verified, not inferred** (2026-08-24). It is the literal dict in
`DBData.wind_speed_str_static`, `app/plot_app/db_entry.py` in `PX4/flight_review`;
the dump contains those four values and `-1`, and nothing else. This was one of the
questions put to the maintainers on the M0 thread. It did not need them.

| value | logs |
|---|---|
| −1 (not given) | 427,068 |
| Calm | 18,348 |
| Breeze | 4,107 |
| Gale | 470 |
| Storm | 402 |

**94.8 % not given is refusal, not a structural artifact.** The obvious explanation
would be that only some uploads are shown the field — `app/tornado_handlers/upload.py`
reads `windSpeed` only when the upload type is `flightreport`. It does not apply here:
cross-tabulating the dump by `type` returns **one** group, `flightreport`, containing
all 450,395 records. Every log in this corpus was asked, and 19 in 20 uploaders
declined.

The reason is in the same file: `is_public = 1` is only reachable inside the
`upload_type == 'flightreport'` branch, so a non-flight-report upload cannot become
public. **The public corpus is the flight-report population by construction** — not a
sample of PX4 uploads, and not a sample that could be widened by asking. That is a
selection statement about all 450k records, and it belongs in every claim made from
them.

**23,327 logs (5.2 %) carry a human-declared wind category** — coarse, subjective,
and entirely independent of both ERA5 and EKF2. It is a cheaper third source than
METAR and it needs no proximity to an airport. Only 1,113 of them are real-hardware
fixed-wing or VTOL, so it strengthens rather than replaces the METAR subset.

It is **declared, not measured**, and by the same person who flew the aircraft: four
levels, chosen after the flight, by someone who already knew how it went. That makes
it a weak cross-check on a disagreement between ERA5 and EKF2, never a referee of one.

## Labels that already exist

`error_labels` uses a fixed vocabulary of eight: Other, Vibration, Airframe-design,
Sensor-error, Component-failure, Software, Human-error, **External-conditions**.
Usage is sparse — External-conditions appears on 160 logs; the largest, Vibration, on
478. `rating` is richer: good 18,328 · great 2,903 · unsatisfactory 1,020 ·
crash_sw_hw 401 · crash_pilot 188.

Sparse, but free, human-applied, and already an ontology — consistent with not
building one.

## What the pilot found (G2), 2026-08-25

100 runs retrieved and converted, 0 conversion failures. Stratified 25 per cell; see
`artifacts/pilot-inventory.json`.

**34 of 100 are usable for H1.** Usable means three things, not two: a `wind` topic with
`windspeed_north`/`windspeed_east`, `vehicle_global_position` with `lat`/`lon`, **and a
recoverable UTC clock**. The binding constraint is not position — present on 87 of 100 —
it is **`wind`, present on only 37**.

| stratum | frame | usable / 25 | rate | implied usable |
|---|---:|---:|---:|---:|
| fixed_wing_or_vtol \| within_window | 6,185 | 18 | 72 % | 4,453 |
| fixed_wing_or_vtol \| older | 10,497 | 13 | 52 % | 5,458 |
| rotorcraft \| older | 40,578 | 2 | 8 % | 3,246 |
| rotorcraft \| within_window | 22,217 | 1 | 4 % | 889 |
| **total** | **79,477** | **34** | **34 %** | **≈ 14,000** |

### The clock is a third requirement, and it is not visible as a missing topic

ULog timestamps are microseconds since boot; ERA5 is indexed by UTC. The only absolute
time in a PX4 log is `vehicle_gps_position.time_utc_usec`, published against the same boot
clock, so the offset is recoverable. Two things about it were found by trying:

**A non-zero `time_utc_usec` is not a valid one, and `fix_type` is not evidence.** Run
`405385f7` reports `fix_type = 3` on all 676 GPS rows with a non-zero `time_utc_usec`
whose values start at 32 seconds and track the boot clock. The receiver never obtained a
date. It has wind, it has position, it looked usable, and it would have joined to weather
in **1970**. Rejected on an epoch check; 12 runs fail the clock requirement in total,
though most were already unusable for other reasons — the net cost is one run.

**`log_date` is the upload date, not the flight date.** 41 of 100 runs recover a GPS time
*earlier* than their `log_date`, by 3 to 2,478 days, and **not one recovers a later time**.
A wrong clock scatters in both directions; a flown-then-uploaded-later corpus lags one
way. A symmetric cross-check rejected all 41 as broken before the asymmetry showed what
they actually were, so the check is one-sided: a flight may precede its upload by years
and cannot follow it. **This also means the ≥300 s duration frame and the retention
strata are indexed by upload date** — which is the right variable for A8, since retention
applies to stored objects, and the wrong one for anything seasonal.

**Fixed-wing and VTOL are 72 % and 52 % usable by retention side; rotorcraft 8 % and 4 %.** That is not a quality
difference, it is a physics one: EKF2 estimates wind by fusing airspeed and sideslip,
which multirotors mostly do not have. `airspeed` is present on 43 runs, closely tracking
`wind`'s 37.

**The consequence is a change of subject, and it should be stated as one.** H1's declared
fallback under a failed estimator check — "narrow to fixed-wing with airspeed" — is not a
fallback. It is the study. Fixed-wing and VTOL are **21 % of the frame but ~75 % of the
usable population**, so a corpus-representative sample is not an H1-representative one,
and any claim from this work is about fixed-wing and VTOL operations unless it says
otherwise.

**This is also why the pilot was stratified rather than drawn proportionally.** A
proportional draw would have been ~85 % rotorcraft and returned roughly 10 usable runs
out of 100 — a result that looks like the study is unviable, when what it actually
measures is that multirotors do not log wind.

**One clean positive.** Every one of the 37 runs carrying `wind` also carries
`variance_north` and `variance_east`. `EstimatorConfig`'s reported variance is
reconstructible whenever there is a wind estimate at all, so its `reconstructible: false`
case does not arise for the variance — the uncertainty ADR-0003 needs is in the logs, not
an assumption.

**Gate G2: pass, with the scope change above.** ~14,000 implied usable runs against a
design point of 10³ is ample headroom; the risk that materialised was composition, not
volume.

## Consequences

1. M2's sample audit is largely already done, on the full population rather than
   ~10² logs. Its remaining content is the part that needs the `.ulg`: field
   coverage, estimator configuration, and geography.
2. Download budget should be spent on a **stratified sample of the ≥ 300 s,
   non-SITL tier**, drawn using these metadata as the sampling frame — but the
   stratification must survive the frame being 28k rather than 79k, because A8 is
   unanswered and the sampler should not be written assuming the larger one.
3. `wind_speed` gives an independent third source for H1 at zero retrieval cost.
