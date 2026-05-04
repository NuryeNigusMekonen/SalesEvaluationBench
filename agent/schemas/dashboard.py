from pydantic import BaseModel, Field

from agent.schemas.briefs import ProspectEnrichmentResponse
from agent.schemas.tools import ToolStatus


class RecentTrace(BaseModel):
    trace_id: str
    event_type: str
    timestamp: str
    company_name: str | None = None
    prospect_id: str | None = None


class DashboardInteractionEvent(BaseModel):
    event_type: str
    channel: str | None = None
    provider: str | None = None
    created_at: str
    payload_summary: str | None = None


class DashboardArtifact(BaseModel):
    name: str
    path: str
    exists: bool = True
    preview: str | None = None
    content_type: str = "text/plain"
    route: str | None = None


class DashboardFlowSummary(BaseModel):
    prospect_id: str | None = None
    company_name: str | None = None
    status: str | None = None
    current_state: str | None = None
    latest_event: str | None = None
    booking_status: str | None = None
    voice_handoff_ready: bool = False
    crm_logged: bool = False


class TenaciousJudgeRuntimeStatus(BaseModel):
    tenacious_judge_enabled: bool = False
    tenacious_comparison_mode: bool = False
    tenacious_comparison_dry_run: bool = True
    adapter_path: str = ""
    adapter_path_exists: bool = False
    required_ml_deps_available: dict[str, bool] = Field(default_factory=dict)
    runtime_mode: str = "fallback"
    last_judge_error: str | None = None
    outbound_is_live: bool = False
    judge_disabled_with_live_outbound_warning: bool = False
    judge_disabled_warning: str | None = None


class TenaciousGovernanceRuntimeStatus(BaseModel):
    tenacious_governance_enabled: bool = False
    tenacious_governance_enforce: bool = False
    log_path: str = ""
    log_exists: bool = False


class DashboardStateResponse(BaseModel):
    total_prospects: int = 0
    total_traces: int = 0
    tool_statuses: list[ToolStatus] = Field(default_factory=list)
    recent_snapshots: list[ProspectEnrichmentResponse] = Field(default_factory=list)
    recent_traces: list[RecentTrace] = Field(default_factory=list)
    latest_flow: DashboardFlowSummary | None = None
    latest_interaction_events: list[DashboardInteractionEvent] = Field(default_factory=list)
    latest_artifacts: list[DashboardArtifact] = Field(default_factory=list)
    tenacious_judge_runtime: TenaciousJudgeRuntimeStatus = Field(
        default_factory=TenaciousJudgeRuntimeStatus
    )
    tenacious_governance_runtime: TenaciousGovernanceRuntimeStatus = Field(
        default_factory=TenaciousGovernanceRuntimeStatus
    )
