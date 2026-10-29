# First Light

My entry to the Light Chaser challenge at Huawei France Tech Arena 2026.

The task was to find the largest value in an array using a simulated focus motor. Reading another position meant moving the motor, and the score depended on more than finding the right answer: readings, travel and changes of direction all mattered. Returning the right index was not enough—the motor had to finish there.

The array has 400–1000 nonnegative integer values. The motor starts at index 0. A call to `run_motor(index)` moves there and reveals that value. The target is the raw maximum, with ties resolved toward the array middle. A case earns 3000 points for parking exactly on the target, or 200 fewer points per step of parking error up to three steps. Then it loses one point per read, one per index traveled, 30 per direction reversal, and one per index overshot to the right of the target. Scores are clamped at zero. At least 200 reads, seven reversals, 200 overshoot steps, more than ten seconds, or parking over three steps away gives zero. The submission must return `0` after physically parking the motor.

The retained solver is the scored V30 source in [first_light/contestant.py](first_light/contestant.py), copied byte for byte. It scans forward with a stride that responds to fitted peak positions. The fit compares localized hill shapes over a linear background, while the best observed position is chosen from exact integer values. It can stop after a sufficiently supported decline or a locally fitted turn. It also has bounded paths for flat readings and a possible rebound. After the forward pass it ranks unsampled positions between readings by interpolation and estimated curvature, then visits selected positions in a descending motor pass. A recovery pass can search farther right when the earlier route is provably doomed to a zero score by overshoot. Repeated reads are cached, and the last physical move parks at the chosen position. [Algorithm notes](docs/ALGORITHM.md) trace these decisions to the source.

From a checkout, use Python 3.12 or newer:

```sh
python -m pip install -e .
python -m first_light demo
python -m first_light benchmark
python -m unittest discover -s tests -v
```

`demo` prints the motor path for one original synthetic hill. `benchmark` runs four deterministic synthetic arrays, including a late second peak and a distant spike. These examples are engineering checks, not competition data or a prediction of official performance. The official judge used Python 3.14 and required standard library only; the solver has no third-party imports. The local commands were run with Python 3.12.14. GitHub Actions is configured to run on 3.12 and 3.14.

The last confirmed official score in the archived scorer evidence is **1655.1**. The V30 submission tied the earlier V29 score on 14 October 2026. The association between that score and this local V30 file follows delivery records; the remote uploaded bytes were not independently hashed. This was not a winning entry, and I do not claim a final rank. Local synthetic scores and their exact command are recorded in [evaluation notes](docs/EVALUATION.md), separately from the official observation.

The experiments taught me to count motor costs alongside localization. V30's extra turn check gave a small improvement on reused development cases, but a constructed later peak still made it fail. Later, a direct fitted record-seeking policy rescued 37 reused cases yet created 33 new zeros and lost 24.38 points per case on average; it was rejected. Those 924 measured-derived variants came from only 35 source scenes, so I treat scene-balanced changes and repeated reuse as essential context, not as independent test performance.

This solver can stop before an arbitrary later maximum; its fitted curves are heuristics, not certificates about unread values. The local simulator scores the documented motor trace but is not the organizer's judge. [Evaluation notes](docs/EVALUATION.md) give the evidence and limitations; [sources and rights](docs/SOURCES.md) explain what was deliberately left out. The code and documentation were developed with AI assistance and reviewed against the archived implementation and records.
