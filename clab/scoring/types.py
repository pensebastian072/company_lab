"""Common auditable shapes every scoring component returns.

Two invariants defended by tests:

  1. `SubTest.earned` is an INTEGER or None. Never a float. A 3.7/4 implies a
     measurement precision the underlying accounting does not have, and for the
     LLM-scored components it would launder model opinion as measurement.

  2. Absent data is `earned=None, status=NO_DATA`, structurally distinct from
     `earned=0, status=SCORED`. A company with no interest-expense tag is not a
     company with terrible interest coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum


class Status(str, Enum):
    SCORED = "scored"
    NO_DATA = "no_data"
    NOT_APPLICABLE = "not_applicable"   # sector profile says the metric is meaningless
    # The value exists but is not believable - a gross margin of 340% is a broken tag
    # pairing, not a spectacular business. Distinct from NO_DATA on purpose: NO_DATA is
    # thin data, DATA_QUALITY_FAIL is a derivation bug, and conflating them hides the
    # second behind the first. Like NO_DATA it earns nothing and lowers coverage.
    DATA_QUALITY_FAIL = "data_quality_fail"


@dataclass
class SubTest:
    key: str                       # "sg_tam_expanding"
    label: str                     # "TAM expanding"
    max_points: int                # 4
    earned: int | None = None      # INTEGER ONLY; None iff status != SCORED
    status: Status = Status.NO_DATA
    inputs: dict = field(default_factory=dict)       # every number used
    provenance: dict = field(default_factory=dict)   # source, tag_used, accn, filed, derived
    rationale: str = ""            # why this score (for LLM sub-tests: the model's words)
    evidence: str | None = None    # verbatim text the score came from (LLM only)
    evidence_unverified: bool = False
    override: int | None = None    # manual override slot; unused at launch
    threshold_note: str = ""       # "3Y CAGR 18.4% >= 15% band -> 4/4"

    def __post_init__(self) -> None:
        if self.earned is not None:
            if isinstance(self.earned, bool) or not isinstance(self.earned, int):
                raise TypeError(
                    f"{self.key}: earned must be int or None, got {type(self.earned).__name__}"
                )
            if not 0 <= self.earned <= self.max_points:
                raise ValueError(
                    f"{self.key}: earned {self.earned} out of range 0..{self.max_points}"
                )
            self.status = Status.SCORED
        elif self.status == Status.SCORED:
            raise ValueError(f"{self.key}: status SCORED requires an integer earned")

    @property
    def effective(self) -> int | None:
        """Manual override wins when set."""
        return self.override if self.override is not None else self.earned

    @property
    def is_llm(self) -> bool:
        return self.provenance.get("source") == "llm"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["effective"] = self.effective
        return d


def scored(
    key: str, label: str, max_points: int, earned: int, **kw
) -> SubTest:
    """Helper: a sub-test that earned a real integer score."""
    return SubTest(key=key, label=label, max_points=max_points,
                   earned=int(earned), status=Status.SCORED, **kw)


def no_data(key: str, label: str, max_points: int, why: str = "", **kw) -> SubTest:
    """Helper: data absent. NOT a zero."""
    kw.setdefault("rationale", why)
    return SubTest(key=key, label=label, max_points=max_points,
                   earned=None, status=Status.NO_DATA, **kw)


def data_quality_fail(key: str, label: str, max_points: int, why: str = "",
                      **kw) -> SubTest:
    """Helper: the number exists and is not believable. NOT a zero, and NOT thin data."""
    kw.setdefault("rationale", why)
    return SubTest(key=key, label=label, max_points=max_points,
                   earned=None, status=Status.DATA_QUALITY_FAIL, **kw)


def not_applicable(key: str, label: str, max_points: int, why: str = "", **kw) -> SubTest:
    """Helper: the metric is meaningless for this sector (see fundamentals.profile)."""
    kw.setdefault("rationale", why)
    return SubTest(key=key, label=label, max_points=max_points,
                   earned=None, status=Status.NOT_APPLICABLE, **kw)


@dataclass
class ComponentScore:
    code: str                      # "SG"
    label: str                     # "Structural Growth"
    max_points: int                # 20
    subtests: list[SubTest] = field(default_factory=list)
    note: str = ""                 # component-level commentary (e.g. BQ killer question)

    @property
    def earned_points(self) -> int:
        return sum(st.effective or 0 for st in self.subtests
                   if st.status == Status.SCORED)

    @property
    def available_points(self) -> int:
        """Points that could have been earned.

        Excludes NO_DATA, NOT_APPLICABLE and DATA_QUALITY_FAIL - only SCORED counts, so
        an unbelievable number lowers coverage rather than being laundered into a 0.
        """
        return sum(st.max_points for st in self.subtests if st.status == Status.SCORED)

    @property
    def not_applicable_points(self) -> int:
        return sum(st.max_points for st in self.subtests
                   if st.status == Status.NOT_APPLICABLE)

    @property
    def no_data_points(self) -> int:
        return sum(st.max_points for st in self.subtests if st.status == Status.NO_DATA)

    @property
    def data_quality_fail_points(self) -> int:
        """Points withheld because the number was not believable, not because it was absent.

        Counted separately from NO_DATA so a company that is unmeasurable can be told
        apart from one whose derivation is broken - the first is a limit of the filing,
        the second is a bug worth fixing.
        """
        return sum(st.max_points for st in self.subtests
                   if st.status == Status.DATA_QUALITY_FAIL)

    @property
    def applicable_points(self) -> int:
        return self.max_points - self.not_applicable_points

    @property
    def coverage(self) -> float:
        """available / applicable. 1.0 when everything applicable was scored."""
        denom = self.applicable_points
        return 1.0 if denom == 0 else self.available_points / denom

    @property
    def is_llm(self) -> bool:
        return any(st.is_llm for st in self.subtests)

    def check_points(self) -> None:
        """Guard: sub-test maxima must sum to the component maximum."""
        total = sum(st.max_points for st in self.subtests)
        if total != self.max_points:
            raise ValueError(
                f"{self.code}: sub-test max_points sum to {total}, expected {self.max_points}"
            )

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "max_points": self.max_points,
            "earned_points": self.earned_points,
            "available_points": self.available_points,
            "applicable_points": self.applicable_points,
            "not_applicable_points": self.not_applicable_points,
            "no_data_points": self.no_data_points,
            "coverage": round(self.coverage, 4),
            "is_llm": self.is_llm,
            "note": self.note,
            "subtests": [st.to_dict() for st in self.subtests],
        }
