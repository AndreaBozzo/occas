# Outreach

M0 is a practitioner check, not a broadcast. What is sent, where, and what came back —
kept here so the record survives the thread.

| Contact | Channel | Sent | Status |
|---|---|---|---|
| PX4 maintainers (@bkueng, @rroche) | [discuss.px4.io/t/49391](https://discuss.px4.io/t/characterising-the-public-log-corpus-450k-logs-and-a-question-about-acceptable-retrieval/49391) | 2026-08-20 | **No reply.** Checked 2026-08-24: 0 replies, 21 views. Two of the four questions have since been answered elsewhere; the remaining two are judgements only they can give. Dev calls happen on the [Dronecode Discord](https://discord.com/invite/dronecode), not the forum — the invite is the one PX4's own [support page](https://docs.px4.io/main/en/contribute/support.html) publishes |
| UAV-SEAD authors | — ([dataset card](https://huggingface.co/datasets/aykutkabaoglu/uav-flight-anomaly-dataset)) | — | **Closed without contact, 2026-08-24.** C1, C2 and C2b were all answerable from the dataset card and the schema. There is no question left that only the authors can answer, so contacting them would cost their time and return nothing |
| Somanagoudar & Mérida (UBC) | email | — | **Narrowed to one question.** Two abstracts — the [paper](https://doi.org/10.1016/j.engappai.2024.109596) and the 2025 UBC thesis, [doi.org/10.14288/1.0445044](https://doi.org/10.14288/1.0445044) — both describe energy prediction validated against measured energy. The thesis DOI resolves to `doi.library.ubc.ca`, which refuses connections from my side but will probably serve you the PDF directly. What remains is a yes/no: *did you compare ERA5 wind against the onboard wind estimate at any point?* A copy of the full text would also close C0 outright |
| SORA practitioners / Specific-category operators | TBD | — | **Not sent — gate G5.** No longer a blank question: [`../05-sora-evidence-map.md`](../05-sora-evidence-map.md) now carries four specific questions read out of [SORA v2.5 Annex E](http://jarus-rpas.org/wp-content/uploads/2024/06/SORA-v2.5-Annex-E-Release.JAR_doc_28pdf.pdf) (the whole 2.5 set is on [jarus-rpas.org/publications](http://jarus-rpas.org/publications/); the EU-side reading is [EASA's Easy Access Rules for UAS](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-unmanned-aircraft-systems-regulations-eu)), and question 2 is the one that decides the gate. **Who** to ask is still open, and is the one part of this I have not narrowed — say the word and I will put together candidate organisations rather than leave you a category |

**Two of the four questions asked there have since been answered without a reply**
(2026-08-24): the `wind_speed` encoding, from `flight_review` source and the metadata
dump itself, and how ERA5T is identified, from ECMWF's documentation. What remains
genuinely needs a maintainer — acceptable retrieval volume, whether `dbinfo` is a
supportable interface, and any position on personal data are judgements about their
service and their users, not facts to be looked up. Asking was still right; waiting
for it was not.

## Blocked on you, not on a reply

Distinct from outreach, and worth keeping separate from it — these do not become
unblocked by waiting:

| What | Why only you | What is already prepared |
|---|---|---|
| A CDS account — [register](https://cds.climate.copernicus.eu/), then [how-to-api](https://cds.climate.copernicus.eu/how-to-api) for the key | Registration under your identity | Nothing else waits on it. ERA5 development runs against the account-free [ARCO-ERA5](https://github.com/google-research/arco-era5) copy ([GCS dataset page](https://cloud.google.com/storage/docs/public-datasets/era5), audit row C5); the account is for the authoritative, CDS-cited retrieval and for confirming `expver` |
| The first `.ulg` download — the decision, not the code | It puts load on someone else's service, and `robots.txt` disallows crawling ([ADR-0005](../adr/0005-sample-from-metadata-not-bulk-download.md)) | The sampling frame exists (≥ 300 s, non-SITL); the stratified sampler is roughly an hour's work and is deliberately unwritten until the retrieval question is settled, either by a reply or by your decision to proceed inside the client's own documented limits |
| C0's full text | Institutional access, or an email | Both abstracts are transcribed into the audit; the gap claim already survives them |
| Any outward-facing post | Yours by division of labour | [ADR-0005](../adr/0005-sample-from-metadata-not-bulk-download.md), [ADR-0007](../adr/0007-licences-travel-with-the-data.md) and [ADR-0008](../adr/0008-retrieve-era5-as-grib.md) are written as raw material for posts |

Every link above was resolved on 2026-08-24, not quoted from memory. Two hosts refuse
connections from here and may work from yours: `open.library.ubc.ca` (the thesis) and
`sciencedirect.com` (the paper's full text).

Replies are transcribed into the document they answer — the source audit, the ODD
prior-art table, the SORA evidence map — with the date and the person who said it.
A thread can be edited or deleted; the audit is the record.
