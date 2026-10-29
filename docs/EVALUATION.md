# Evaluation and provenance

## Source identity

The source archive supplied for this publication was `First_Light_Research_Checkpoint_2026-10-12.zip`, SHA256 `64eec4fc488ecd79039dbe6aaffbe38fd57240b27abc47c5c1a373ae7df2920c`. Its ZIP CRC check passed. No Library file resolution tool was available in this session, so the attached archive was used.

The published solver is exactly `focus_hunter/releases/v30_trial/contestant.py` from that archive. Its SHA256 is `149cca767952af550ecd75905a1f460d726798a7707d47e2201e9c60ec25b79c`. The test suite verifies this hash. The archived `versions/v30_scored/result.json`, `artifacts/v31/official_feedback_43720.json`, and `releases/v30_trial/release.json` each record 1655.1 for submission 43720. That official score was read from a scorer screenshot on 14 October 2026; the upload's remote bytes were not independently hashed. It is a public scorer observation, not a final private result or rank.

## Reproducible local results

`python -m first_light benchmark` runs only the original synthetic arrays in this repository. On Python 3.12.14, the command produced:

| Array | Target | Final park | Score | Reads | Travel | Reversals | Overshoot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| broad_hill | 92 | 92 | 2751 | 31 | 142 | 2 | 16 |
| two_hills | 515 | 145 | 0 | 71 | 307 | 2 | 0 |
| flat | 200 | 200 | 2133 | 49 | 592 | 1 | 196 |
| hidden_spike | 999 | 90 | 0 | 29 | 160 | 2 | 0 |

The mean of these four deliberately mixed examples is 1221.00. It describes this small synthetic set only. The `demo` command prints the complete path of `broad_hill`; its final query is index 92, physically parking on the maximum.

The original development bank held 1,644 cases. Its 924 measured-derived variants came from 35 source scenes after multiple transformations and repeated use in research. They were neither 924 independent scenes nor an unseen test set. `artifacts/v30/final_decision.json` recorded a +0.642 mean change over the prior candidate on all 1,644 development cases and +0.305 over the 924 measured-derived variants. Neither figure predicts an official score. The later V66 screen lost 24.378 points per variant by ordinary case mean, while its equal-scene mean changed by +7.033; it had 37 rescues and 33 new zeros and was rejected. The scene-balanced mean gives each source scene equal weight and exposes the effect of repeatedly sampling one scene.

The archived V64 reflected-pair experiment was also rejected: its ordinary case mean fell 12.540 points over the same 924 reused variants despite a +6.049 equal-scene mean. In both experiments, an apparently useful signal changed the route enough to add movement and overshoot costs. The selected V30 source was not retuned for this publication.

The local simulator implements the published score terms and includes an elapsed-time zero condition. It runs the solver in-process, so it measures elapsed time after a call rather than preempting it at ten seconds. It does not replicate the organizer's runtime, memory accounting, protocol failure handling or hidden data. The official environment specified Python 3.14 and 10 MB excluding the interpreter. Local commands used Python 3.12.14; [GitHub Actions run 40898966320](https://github.com/faitholopade/first-light/actions/runs/40898966320) passed installation, tests and benchmark on both Python 3.12 and 3.14.
