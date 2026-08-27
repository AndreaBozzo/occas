# 06 — Limitations

Maintained continuously, not written at the end. A limitation discovered during the
work is added here the day it is discovered.

## Sample

- Public PX4 logs are an **observational convenience sample**. They over-represent
  test flights, SITL, development airframes, and users who uploaded a log because
  something went wrong or because they wanted help. They are not a production fleet.
- Geography, season and vehicle mix are whatever the uploader population happened to
  be. Any rate computed over the corpus is a rate over that population and nothing
  wider.

## Measurement

- **Neither wind source is ground truth.** ERA5 is a 0.25° hourly reanalysis; the PX4
  wind estimate is an EKF2 output whose quality depends on platform, sensing and
  calibration. Disagreement does not identify which source is wrong.
- Multicopter wind estimation depends on drag coefficients being correctly calibrated.
  Whether they are is generally not recoverable from the log.
- ERA5T, the preliminary product, may be superseded by the final release, typically
  within 2-3 months. Results record which was retrieved and when.
- METAR, where used, is a 10 m measurement over open flat terrain by construction, and
  is comparable only under stated restricted conditions.

## Proxies

- GNSS geometry is not received signal quality.
- A DEM is not an obstacle map.
- An EKF estimate is not a measurement.
- A logged parameter is a configuration, not a behaviour.
- **The 3.0 m s⁻¹ usefulness band is asserted, not cited.** H1 calls the reanalysis a
  useful proxy in a regime when the upper 95% limit of agreement on the vector
  difference magnitude is at most 3.0 m s⁻¹
  ([`adr/0015`](adr/0015-what-makes-the-reanalysis-a-useful-proxy.md)). It was sized
  against manufacturer-declared small-UAS wind limits of roughly 10–12 m s⁻¹, so that
  a proxy carrying 3 m s⁻¹ of disagreement still leaves a usable margin against a
  10 m s⁻¹ limit. No standard states it and no regulator endorses it. It was fixed
  before any agreement statistic existed, which makes it honest, not authoritative.
- **EKF2's reported variance is a filter's self-assessment.** The estimator-relative
  ratio reported beside that band is a second view of the disagreement, not a second
  source of truth, and it passes most easily where the onboard estimate is least sure
  of itself.

## Structural

- Event definitions are the most fragile part of the project. H1 is deliberately
  constructed not to depend on them.
- **UAV-SEAD cannot serve H1.** 8.8% of its flight time has global position, its
  schema carries no wind or airspeed topic, and it is multi-rotor and largely indoor.
  The assumed trade — their annotations for our context — does not hold for the wind
  study, and any event work using it draws on a different population from the public
  PX4 corpus. Recorded as C2b in the source audit.
- Estimator configuration may not be reconstructible from every log. If it is broadly
  absent, the study narrows to fixed-wing with airspeed (risk register, M2).
- Firmware and schema drift across versions is expected; a support matrix and version
  registry are required before cross-version claims.

## Publication

- Raw geolocated trajectories are not redistributed; published coordinates are
  generalised. Some analyses are therefore not exactly reproducible from published
  artifacts alone — they are reproducible from the original source via the published
  pipeline, which is the weaker but honest guarantee, and it is stated as such.
