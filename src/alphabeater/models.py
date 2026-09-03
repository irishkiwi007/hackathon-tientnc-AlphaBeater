"""Typed artifacts exchanged by AlphaBeater components."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Direction(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class MarketObservation(StrictModel):
    as_of: str = Field(description="ISO-8601 timestamp for the point-in-time snapshot")
    universe: list[str] = Field(min_length=1, max_length=100)
    evidence: list[str] = Field(min_length=1, max_length=20)


class MarketHypothesis(StrictModel):
    title: str = Field(min_length=5, max_length=120)
    mechanism: str = Field(min_length=20, max_length=1200)
    expected_direction: Direction
    horizon_days: int = Field(ge=1, le=60)
    evidence_used: list[str] = Field(min_length=1, max_length=10)
    falsification_criteria: list[str] = Field(min_length=1, max_length=8)


class FactorCandidate(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,49}$")
    expression: str = Field(min_length=3, max_length=300)
    rationale: str = Field(min_length=15, max_length=800)
    required_fields: list[str] = Field(min_length=1, max_length=12)
    horizon_days: int = Field(ge=1, le=60)
    expected_direction: Direction


class FactorProposal(StrictModel):
    candidates: list[FactorCandidate] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def names_are_unique(self) -> "FactorProposal":
        names = [candidate.name for candidate in self.candidates]
        if len(names) != len(set(names)):
            raise ValueError("factor candidate names must be unique")
        return self


class ResearchBundle(StrictModel):
    hypothesis: MarketHypothesis
    factors: FactorProposal
