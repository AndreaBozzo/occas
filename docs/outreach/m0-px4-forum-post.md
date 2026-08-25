> **POSTED 2026-08-20** as AndreaBozzo, in category PX4:
> <https://discuss.px4.io/t/characterising-the-public-log-corpus-450k-logs-and-a-question-about-acceptable-retrieval/49391>
>
> Awaiting reply. Answers are transcribed into
> [`../01-source-audit.md`](../01-source-audit.md) with date and author, not left
> to sit in the thread.

**Title:** Characterising the public log corpus (450k logs) — and a question about acceptable retrieval

**Where:** https://discuss.px4.io — register at https://discuss.px4.io/signup

**Category:** **PX4** (https://discuss.px4.io/c/px4/25). It is the main development
category (6,841 topics) and where the maintainers actually read. `Flight Testing`
(https://discuss.px4.io/c/flight-testing/10) is scoped to "flight results and logs",
which fits the content but not the audience — this is a question about the log service
and its data policy, not about a flight.

**Address:** @bkueng and @rroche settled the CC-BY question in
["License for the dataset"](https://discuss.px4.io/t/42819) (Dec 2024), so they are
the right people to tag.

**Mirror:** Dronecode Discord, https://discord.com/invite/Dronecode — @rroche pointed
people there in that same thread, noting the dev calls moved off Jitsi. Post the forum
link there rather than the whole text.

---

Hi all,

I'm building a small open research project that links real flight telemetry to the
external conditions it was flown in — the first question being how well ERA5
reanalysis wind agrees with the onboard EKF2 wind estimate, across real flights and
across regimes. Neither is ground truth, so it's an agreement study, not a validation
of one against the other.

Before downloading anything, I characterised the public corpus from the metadata
served at `review.px4.io/dbinfo` (one request; it redirects to a daily CDN dump).
Sharing the numbers here because I think they're useful on their own, and because I'd
rather ask about retrieval than assume.

### What's in the public corpus (as of 2026-08-20)

- **450,395 public logs**, 26 metadata fields populated on every record
- **33,762 (7.5%) are `PX4_SITL`** — cleanly identifiable from metadata alone
- **416,633 real-hardware logs, totalling ~24,924 flight-hours**
- **Median log duration is 79 s.** p90 is 520 s. Only **79,477 logs exceed 5 minutes**
- **60,079 fixed-wing or VTOL** real-hardware logs (Fixed Wing 26,289 · VTOL Standard
  24,707 · Tiltrotor 10,545 · tailsitters ~6,809)
- `estimator` is EKF2 on 99.2% of logs
- **23,327 logs (5.2%) carry an uploader-declared `wind_speed`** — Calm 18,348,
  Breeze 4,107, Gale 470, Storm 402
- `error_labels` are sparse: Vibration 478, Sensor-error 313, External-conditions 160,
  and similar. `rating` is denser: good 18,328, great 2,903, unsatisfactory 1,020,
  crash_sw_hw 401, crash_pilot 188

> **Correction, 2026-08-25 — found here, not yet posted to the thread.** The fixed-wing
> and VTOL subtypes above are wrong as sent. 60,079 is the real-hardware total, but the
> subtypes printed beside it were counted over *all* logs, SITL included, so they sum to
> 68,350 against a stated 60,079. The real-hardware split is Fixed Wing 23,301 · VTOL
> Standard 21,462 · Tiltrotor VTOL 9,096 · tailsitters 5,993 · VTOL reserved 227.
> **Every other figure in this post was re-verified against the artifact and stands.**
> The sent text is left as sent, because this file is the record of what was sent;
> whether to correct the thread is yours. Cause and fix:
> [ADR-0010](../adr/0010-manifests-are-verified-against-the-repository.md).

The duration distribution surprised me most. A lot of what I'd have naively counted as
"flights" are bench runs and short hops, which matters a great deal if you're joining
against an hourly reanalysis.

### Questions

1. **Is the `dbinfo` CDN dump intended as a public interface?** It's exactly what I
   needed and it kept my traffic off your origin entirely. I'd like to depend on it,
   but I don't want to build on something that's an implementation detail.

2. **What's an acceptable retrieval volume and rate for the `.ulg` files?**
   `app/download_logs.py` documents 10 requests/minute, a default cap of 10, and a
   confirmation above 100 — but `logs.px4.io/robots.txt` is `Allow: /` followed by
   `Disallow: /*`, which reads as "please don't crawl this". I'd plan on a stratified
   sample of roughly 1,000–2,000 logs from the >5-minute, non-SITL tier, at the
   documented rate, not a bulk pull. Is that welcome, tolerated, or not? I saw the note
   in the script about Dronecode funding the bandwidth and would rather not be a
   nuisance.

3. **Is there a position on personal data in the public logs?** CC-BY settles the
   copyright question, but takeoff/landing coordinates are a separate matter. My
   working policy is to publish only derived and aggregate features with generalised
   coordinates, plus the pipeline so anyone can re-run it against the original source —
   never raw trajectories. If there's an existing view on this I'd rather align with it.

4. **Am I reading `wind_speed` correctly** as uploader-declared, `{0: Calm, 5: Breeze,
   8: Gale, 10: Storm}`, `-1` meaning not given? If so it's a genuinely useful
   independent reference and I'd like to use it.

### What I'd give back

Everything is Apache-2.0 with CC-BY attribution carried through: the pipeline, the
schemas, and the corpus characterisation above as a reproducible artifact rather than
a forum post. Conversion is delegated to `ulog-convert` from `flight-review-rs` — I'm
deliberately not writing a parser, and would rather contribute upstream where something
is missing.

Happy to be told the framing is wrong, or that someone has already done this.

Thanks,
Andrea
