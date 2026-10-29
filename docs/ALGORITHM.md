# How V30 searches

The published `contestant.py` is the 26,867-byte V30 release. It is unchanged so that its hash remains comparable with the archived release. The local simulator injects `run_motor` and calls the actual `find_peak` entry point; the solver still returns integer `0` after parking.

The first pass moves right. It begins with a 12-index stride and can adjust that stride between 6 and 24 using the median peak position of fitted models. `_Posterior` fits localized Gaussian-like and Lorentzian-like hills plus a linear background to coarse observations. Its `future` value is model weight beyond the current position, not a calibrated probability that no larger raw value exists. The stopping rule combines this fit with observed decline, a lag from the sampled best, and a signal-to-noise check. `_confirm_turn` can stop sooner when a locally concave turn has enough observations on both sides. A flat-run cap and a bounded rebound continuation handle two special observed patterns.

For each unobserved position between coarse samples, the first pass computes a linear interpolation plus a curvature and local-noise allowance. It selects the highest-ranked positions within a call budget and visits them in descending index order. The candidate comparison and final best use exact raw integers with the contest midpoint tie rule. An observed new record may replace the previous best; there is no claim that the selected set contains every possible maximum.

`_virtual_solve` can run a second forward scan only when the first route has already reached a rightmost position at least 203 beyond its parked result. In that state no target within three indices of the park could avoid the 200-step overshoot zero rule. The recovery scan reserves calls for another descending refinement and one final park. It is a conditional attempt to rescue a zero, not a global search guarantee.

`_solve` caches static observations so the actual motor skips redundant moves while the virtual route maintains its own budget accounting. It makes a last physical `run_motor(target)` call when the motor is elsewhere. The source guards a maximum of 199 virtual reads and six reversals; the simulator tests actual trace accounting separately.

The failure modes are concrete. A distant second hill can be missed after early stopping. A narrow unread spike is indistinguishable from an array without it along the same query path. Exploring farther also risks travel and overshoot penalties, including an immediate zero at the 200-step limit.
