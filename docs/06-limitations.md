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

## Structural

- Event definitions are the most fragile part of the project. H1 is deliberately
  constructed not to depend on them.
- Estimator configuration may not be reconstructible from every log. If it is broadly
  absent, the study narrows to fixed-wing with airspeed (risk register, M2).
- Firmware and schema drift across versions is expected; a support matrix and version
  registry are required before cross-version claims.

## Publication

- Raw geolocated trajectories are not redistributed; published coordinates are
  generalised. Some analyses are therefore not exactly reproducible from published
  artifacts alone — they are reproducible from the original source via the published
  pipeline, which is the weaker but honest guarantee, and it is stated as such.
