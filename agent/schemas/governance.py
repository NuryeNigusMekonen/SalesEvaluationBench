from typing import Literal

from pydantic import BaseModel, Field


class GovernanceEvidence(BaseModel):
    evidence_id: str
    detective: str
    finding: str
    severity: Literal["low", "medium", "high", "critical"]
    supported: bool
    details: str
    cited_fields: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class GovernanceJudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    verdict: Literal["pass", "fail", "needs_human_review"]
    argument: str
    cited_evidence: list[str] = Field(default_factory=list)


class GovernanceReview(BaseModel):
    review_id: str
    timestamp_utc: str
    prospect_id: str | None = None
    company_name: str | None = None
    candidate_action_type: str
    candidate_channel: str
    candidate_output: str
    primary_risk_focus: str = "none"
    overall_score: float = Field(ge=1.0, le=5.0)
    final_verdict: Literal["pass", "fail", "needs_human_review"]
    final_decision: Literal["allow", "block", "human_review"]
    dissent_summary: str | None = None
    remediation_plan: list[str] = Field(default_factory=list)
    rules_applied: list[str] = Field(default_factory=list)
    governance_enabled: bool = True
    enforcement_applied: bool = False
    enforcement_reason: str | None = None
    evidences: list[GovernanceEvidence] = Field(default_factory=list)
    opinions: list[GovernanceJudicialOpinion] = Field(default_factory=list)
