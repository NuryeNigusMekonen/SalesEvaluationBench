from typing import Literal

from pydantic import BaseModel, Field


class ConversationDecision(BaseModel):
    next_action: Literal["send_email", "send_sms", "book_meeting", "handoff_human"]
    channel: Literal["email", "sms", "calendar", "human", "voice"]
    reply_draft: str
    needs_human: bool = False
    risk_flags: list[str] = Field(default_factory=list)
    trace_tags: list[str] = Field(default_factory=list)
    reply_artifact_ref: str | None = None
    judge_review: dict[str, object] = Field(default_factory=dict)
    governance_review: dict[str, object] = Field(default_factory=dict)
