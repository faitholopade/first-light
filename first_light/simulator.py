"""Small local motor and score model for static sharpness arrays.

The scoring terms follow the published Focus Hunter statement. This is an
independent implementation, not a copy of the organizer's interactor.
"""

from dataclasses import asdict, dataclass
from time import perf_counter

from . import contestant


@dataclass(frozen=True)
class Result:
    target_index: int
    final_index: int
    distance: int
    query_count: int
    travel: int
    search_cost: int
    reversal_count: int
    rightmost_index: int
    overshoot: int
    score: int
    trace: tuple[int, ...]

    def as_dict(self):
        return asdict(self)


def main_peak(values):
    """Resolve a raw-value maximum toward the middle; use lower index for a tie."""
    if not values:
        raise ValueError("a case needs at least one value")
    maximum = max(values)
    return min(
        (i for i, value in enumerate(values) if value == maximum),
        key=lambda i: (abs(2 * i - (len(values) - 1)), i),
    )


def score_trace(values, trace, *, elapsed_seconds=0.0):
    """Score actual motor calls, including a final parking call if there was one."""
    if not values or any(type(value) is not int or value < 0 for value in values):
        raise ValueError("sharpness values must be nonnegative integers")
    if elapsed_seconds < 0:
        raise ValueError("elapsed time cannot be negative")
    trace = tuple(trace)
    if any(type(i) is not int or not 0 <= i < len(values) for i in trace):
        raise ValueError("motor index outside the array")
    target = main_peak(values)
    position = 0
    direction = 0
    travel = 0
    reversals = 0
    rightmost = 0
    for index in trace:
        delta = index - position
        new_direction = (delta > 0) - (delta < 0)
        if direction and new_direction and direction != new_direction:
            reversals += 1
        if new_direction:
            direction = new_direction
        travel += abs(delta)
        position = index
        rightmost = max(rightmost, index)
    distance = abs(position - target)
    overshoot = max(0, rightmost - target)
    cost = len(trace) + travel
    invalid = (
        distance > 3
        or len(trace) >= 200
        or reversals >= 7
        or overshoot >= 200
        or elapsed_seconds > 10
    )
    score = 0 if invalid else max(0, 3000 - 200 * distance - cost - 30 * reversals - overshoot)
    return Result(target, position, distance, len(trace), travel, cost,
                  reversals, rightmost, overshoot, score, trace)


class Motor:
    def __init__(self, values):
        self.values = tuple(values)
        self.trace = []

    def read(self, index):
        if type(index) is not int or not 0 <= index < len(self.values):
            raise ValueError(f"invalid motor index: {index!r}")
        self.trace.append(index)
        return self.values[index]


def run_solver(values):
    """Exercise the submission's real find_peak entry point via an injected motor."""
    values = tuple(values)
    if not 400 <= len(values) <= 1000:
        raise ValueError("competition arrays have length 400..1000")
    motor = Motor(values)
    previous = getattr(contestant, "run_motor", None)
    had_previous = hasattr(contestant, "run_motor")
    contestant.run_motor = motor.read
    started = perf_counter()
    try:
        status = contestant.find_peak(len(values))
    finally:
        elapsed = perf_counter() - started
        if had_previous:
            contestant.run_motor = previous
        else:
            del contestant.run_motor
    if type(status) is not int or status != 0:
        raise RuntimeError(f"submission returned {status!r}")
    return score_trace(values, motor.trace, elapsed_seconds=elapsed)
