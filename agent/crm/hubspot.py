import json
from datetime import datetime, timezone
from urllib.error import HTTPError

from agent.config import settings
from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.schemas.tools import ToolExecutionResult, ToolStatus
from agent.utils.http import request_json


class HubSpotMCPClient:
    def __init__(self) -> None:
        self._contact_property_names: set[str] | None = None

    def status(self) -> ToolStatus:
        configured = bool(settings.hubspot_access_token)
        return ToolStatus(
            name="hubspot",
            label="HubSpot MCP CRM",
            mode="configured" if configured else "mock",
            configured=configured,
            available=True,
            details=(
                "HubSpot MCP integration covers contact upsert, enrichment field writes, "
                "and activity logging. Local artifacts are written unless a HubSpot token is configured."
            ),
        )

    def _write_artifact(self, payload: dict, prospect_id: str) -> str:
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = settings.outbox_dir / f"{prospect_id}_hubspot.json"
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(artifact_path)

    def _guard_crm_action(
        self,
        *,
        prospect_id: str,
        prospect_context: dict,
        agent_output: dict,
        action_type: str,
    ) -> ToolExecutionResult | None:
        review = review_before_action(
            {
                "prospect_context": prospect_context,
                "hiring_signal_brief": prospect_context.get("hiring_signal_brief", {}),
                "competitor_gap_brief": prospect_context.get("competitor_gap_brief", {}),
                "agent_output": json.dumps(agent_output, ensure_ascii=False, default=str),
                "action_type": action_type,
                "channel": "crm",
                "prospect_id": prospect_id,
            }
        )
        if review["allow"]:
            return None
        return ToolExecutionResult(
            name="hubspot",
            mode=self.status().mode,
            status="skipped",
            message=f"HubSpot action blocked by Tenacious judge: {review['reason']}",
        )

    def _contact_properties(self, payload: dict) -> dict[str, object]:
        return {
            "email": payload.get("email"),
            "firstname": (payload.get("contact_name") or payload.get("company_name") or "").split(" ")[0],
            "phone": payload.get("phone"),
            "company": payload.get("company_name"),
            "website": payload.get("company_domain"),
            "lifecyclestage": "lead",
        }

    def _preview_result(
        self,
        *,
        action_message: str,
        artifact_ref: str,
        external_id: str | None = None,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            name="hubspot",
            mode="mock",
            status="previewed",
            message=action_message,
            artifact_ref=artifact_ref,
            external_id=external_id,
        )

    def _enrichment_properties(self, payload: dict) -> dict[str, object]:
        return {
            "tenacious_segment": payload.get("segment"),
            "tenacious_segment_confidence": payload.get("segment_confidence"),
            "tenacious_ai_maturity_score": payload.get("ai_maturity_score"),
            "tenacious_bench_match": json.dumps(payload.get("bench_match", {})),
            "tenacious_last_inbound_channel": payload.get("last_inbound_channel"),
            "tenacious_last_reply_next_action": payload.get("last_reply_next_action"),
            "tenacious_trace_id": payload.get("trace_id"),
            "tenacious_booking_status": payload.get("booking_status"),
            # Signal fields for rubric visibility
            "tenacious_funding_signal": payload.get("funding_signal"),
            "tenacious_job_post_velocity": payload.get("job_post_velocity"),
            "tenacious_layoff_signal": payload.get("layoff_signal"),
            "tenacious_leadership_change": payload.get("leadership_change"),
            "tenacious_company_size": payload.get("company_size"),
            "tenacious_industry": payload.get("industry"),
            "tenacious_enrichment_timestamp": payload.get("enrichment_timestamp"),
        }


    def _get_contact_property_names(self) -> set[str]:
        if self._contact_property_names is not None:
            return self._contact_property_names
        _, response, _ = request_json(
            "GET",
            f"{settings.hubspot_base_url}/crm/v3/properties/contacts",
            headers={
                "Authorization": f"Bearer {settings.hubspot_access_token}",
            },
        )
        self._contact_property_names = {
            item.get("name")
            for item in response.get("results", [])
            if item.get("name")
        }
        return self._contact_property_names

    def _supported_enrichment_properties(self, enrichment_fields: dict[str, object]) -> tuple[dict[str, object], list[str]]:
        filtered = {
            key: str(value) if not isinstance(value, str) else value
            for key, value in enrichment_fields.items()
            if value is not None
        }
        property_names = self._get_contact_property_names()
        supported = {
            key: value
            for key, value in filtered.items()
            if key in property_names
        }
        unsupported = sorted(key for key in filtered if key not in supported)
        return supported, unsupported

    def _summarize_metadata(self, metadata: dict | None) -> dict:
        metadata = metadata or {}
        side_effects = metadata.get("side_effects")
        summarized_side_effects = []
        if isinstance(side_effects, list):
            for item in side_effects[:5]:
                if isinstance(item, dict):
                    summarized_side_effects.append(
                        {
                            "name": item.get("name"),
                            "status": item.get("status"),
                            "message": item.get("message"),
                        }
                    )
        summary = {
            "risk_flags": metadata.get("risk_flags"),
            "channel_state": metadata.get("channel_state"),
            "side_effects": summarized_side_effects or None,
        }
        return {key: value for key, value in summary.items() if value not in (None, [], {})}

    def _build_note_body(self, activity_type: str, activity_summary: str, metadata: dict | None) -> str:
        metadata = metadata or {}
        signal_lines = ""
        signals = metadata.get("signals")
        if signals:
            signal_lines = "\n\nSignals:\n" + "\n".join(
                f"  {s.get('name', '?')}: {s.get('summary', '')} (conf {s.get('confidence', 0):.0%})"
                for s in signals
            )
        enrichment_lines = ""
        for key in ("funding_signal", "job_post_velocity", "layoff_signal", "leadership_change",
                    "company_size", "industry", "enrichment_timestamp", "ai_maturity_score",
                    "segment", "segment_confidence", "bench_match"):
            val = metadata.get(key)
            if val is not None:
                enrichment_lines += f"\n  {key}: {val}"
        if enrichment_lines:
            enrichment_lines = "\n\nEnrichment fields:" + enrichment_lines

        meta_summary = json.dumps(self._summarize_metadata(metadata), sort_keys=True)
        note_body = (
            f"[{activity_type}] {activity_summary}"
            f"{signal_lines}{enrichment_lines}"
            f"\n\nmetadata={meta_summary}"
        )
        if len(note_body) > 4000:
            note_body = note_body[:3997] + "..."
        return note_body

    def _build_note_properties(
        self,
        *,
        activity_type: str,
        activity_summary: str,
        metadata: dict | None,
        logged_at: str,
    ) -> dict[str, str]:
        return {
            "hs_timestamp": logged_at,
            "hs_note_body": self._build_note_body(
                activity_type,
                activity_summary,
                metadata,
            ),
        }

    def _find_contact(self, email: str) -> str | None:
        _, search_response, _ = request_json(
            "POST",
            f"{settings.hubspot_base_url}/crm/v3/objects/contacts/search",
            headers={
                "Authorization": f"Bearer {settings.hubspot_access_token}",
            },
            payload={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }
                        ]
                    }
                ],
                "limit": 1,
            },
        )
        results = search_response.get("results", [])
        return str(results[0]["id"]) if results else None

    def sync_contact_profile(self, payload: dict, prospect_id: str) -> ToolExecutionResult:
        artifact_payload = {
            "action": "sync_contact_profile",
            "payload": payload,
            "transport": "hubspot_mcp",
        }
        blocked = self._guard_crm_action(
            prospect_id=prospect_id,
            prospect_context=payload,
            agent_output=artifact_payload,
            action_type="crm_update",
        )
        if blocked:
            return blocked
        artifact_ref = self._write_artifact(artifact_payload, prospect_id)
        status = self.status()
        email = payload.get("email")
        if status.configured and email:
            try:
                contact_id = self._find_contact(str(email))
                properties = self._contact_properties(payload)
                if contact_id:
                    request_json(
                        "PATCH",
                        f"{settings.hubspot_base_url}/crm/v3/objects/contacts/{contact_id}",
                        headers={
                            "Authorization": f"Bearer {settings.hubspot_access_token}",
                        },
                        payload={"properties": properties},
                    )
                else:
                    _, create_response, _ = request_json(
                        "POST",
                        f"{settings.hubspot_base_url}/crm/v3/objects/contacts",
                        headers={
                            "Authorization": f"Bearer {settings.hubspot_access_token}",
                        },
                        payload={"properties": properties},
                    )
                    contact_id = str(create_response.get("id"))
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="executed",
                    message="HubSpot MCP contact profile synced successfully.",
                    artifact_ref=artifact_ref,
                    external_id=contact_id,
                )
            except HTTPError as exc:
                if exc.code in {401, 403}:
                    return self._preview_result(
                        action_message=(
                            "HubSpot rejected the current credentials or portal access; "
                            f"kept the contact artifact locally instead ({exc})."
                        ),
                        artifact_ref=artifact_ref,
                    )
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP contact sync failed: {exc}",
                    artifact_ref=artifact_ref,
                )
            except OSError as exc:
                return self._preview_result(
                    action_message=(
                        "HubSpot live sync was unavailable from this environment; "
                        f"kept the contact artifact locally instead ({exc})."
                    ),
                    artifact_ref=artifact_ref,
                )
            except Exception as exc:
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP contact sync failed: {exc}",
                    artifact_ref=artifact_ref,
                )
        return ToolExecutionResult(
            name="hubspot",
            mode=status.mode,
            status="previewed",
            message="HubSpot MCP contact payload prepared and recorded.",
            artifact_ref=artifact_ref,
        )

    def write_enrichment_fields(
        self,
        contact_id: str | None,
        enrichment_fields: dict,
        prospect_id: str,
    ) -> ToolExecutionResult:
        artifact_payload = {
            "action": "write_enrichment_fields",
            "contact_id": contact_id,
            "enrichment_fields": enrichment_fields,
            "transport": "hubspot_mcp",
        }
        blocked = self._guard_crm_action(
            prospect_id=prospect_id,
            prospect_context={"prospect_id": prospect_id},
            agent_output=artifact_payload,
            action_type="crm_update",
        )
        if blocked:
            return blocked
        artifact_ref = self._write_artifact(artifact_payload, prospect_id)
        status = self.status()
        if status.configured and contact_id:
            try:
                supported_fields, unsupported_fields = self._supported_enrichment_properties(enrichment_fields)
                if not supported_fields:
                    return ToolExecutionResult(
                        name="hubspot",
                        mode="mock",
                        status="previewed",
                        message=(
                            "HubSpot contact sync is live, but no matching custom enrichment properties "
                            f"were available on the portal. Skipped remote write for: {', '.join(unsupported_fields) or 'none'}."
                        ),
                        artifact_ref=artifact_ref,
                        external_id=contact_id,
                    )
                request_json(
                    "PATCH",
                    f"{settings.hubspot_base_url}/crm/v3/objects/contacts/{contact_id}",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_access_token}",
                    },
                    payload={"properties": supported_fields},
                )
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="executed",
                    message="HubSpot MCP enrichment fields written successfully.",
                    artifact_ref=artifact_ref,
                    external_id=contact_id,
                )
            except HTTPError as exc:
                if exc.code == 400:
                    return ToolExecutionResult(
                        name="hubspot",
                        mode="mock",
                        status="previewed",
                        message=(
                            "HubSpot rejected the enrichment-property payload for this portal; "
                            f"kept the enrichment artifact locally instead ({exc})."
                        ),
                        artifact_ref=artifact_ref,
                        external_id=contact_id,
                    )
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP enrichment write failed: {exc}",
                    artifact_ref=artifact_ref,
                )
            except OSError as exc:
                return self._preview_result(
                    action_message=(
                        "HubSpot live enrichment write was unavailable from this environment; "
                        f"kept the enrichment artifact locally instead ({exc})."
                    ),
                    artifact_ref=artifact_ref,
                    external_id=contact_id,
                )
            except Exception as exc:
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP enrichment write failed: {exc}",
                    artifact_ref=artifact_ref,
                )
        return ToolExecutionResult(
            name="hubspot",
            mode=status.mode,
            status="previewed",
            message="HubSpot MCP enrichment write recorded locally.",
            artifact_ref=artifact_ref,
            external_id=contact_id,
        )

    def log_activity(
        self,
        contact_id: str | None,
        *,
        activity_type: str,
        activity_summary: str,
        prospect_id: str,
        metadata: dict | None = None,
    ) -> ToolExecutionResult:
        artifact_payload = {
            "action": "log_activity",
            "contact_id": contact_id,
            "activity_type": activity_type,
            "activity_summary": activity_summary,
            "metadata": metadata or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "transport": "hubspot_mcp",
        }
        blocked = self._guard_crm_action(
            prospect_id=prospect_id,
            prospect_context={"prospect_id": prospect_id, **(metadata or {})},
            agent_output=artifact_payload,
            action_type="crm_update",
        )
        if blocked:
            return blocked
        artifact_ref = self._write_artifact(artifact_payload, prospect_id)
        status = self.status()
        if status.configured and contact_id:
            try:
                request_json(
                    "POST",
                    f"{settings.hubspot_base_url}/crm/v3/objects/notes",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_access_token}",
                    },
                    payload={
                        "properties": self._build_note_properties(
                            activity_type=activity_type,
                            activity_summary=activity_summary,
                            metadata=metadata,
                            logged_at=artifact_payload["logged_at"],
                        ),
                        "associations": [
                            {
                                "to": {"id": contact_id},
                                "types": [
                                    {
                                        "associationCategory": "HUBSPOT_DEFINED",
                                        "associationTypeId": 202,
                                    }
                                ],
                            }
                        ],
                    },
                )
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="executed",
                    message="HubSpot MCP activity logged successfully.",
                    artifact_ref=artifact_ref,
                    external_id=contact_id,
                )
            except HTTPError as exc:
                if exc.code == 400:
                    return ToolExecutionResult(
                        name="hubspot",
                        mode="mock",
                        status="previewed",
                        message=(
                            "HubSpot rejected the activity-note payload for this portal; "
                            f"kept the activity artifact locally instead ({exc})."
                        ),
                        artifact_ref=artifact_ref,
                        external_id=contact_id,
                    )
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP activity log failed: {exc}",
                    artifact_ref=artifact_ref,
                )
            except OSError as exc:
                return self._preview_result(
                    action_message=(
                        "HubSpot live activity logging was unavailable from this environment; "
                        f"kept the activity artifact locally instead ({exc})."
                    ),
                    artifact_ref=artifact_ref,
                    external_id=contact_id,
                )
            except Exception as exc:
                return ToolExecutionResult(
                    name="hubspot",
                    mode="configured",
                    status="error",
                    message=f"HubSpot MCP activity log failed: {exc}",
                    artifact_ref=artifact_ref,
                )
        return ToolExecutionResult(
            name="hubspot",
            mode=status.mode,
            status="previewed",
            message="HubSpot MCP activity log recorded locally.",
            artifact_ref=artifact_ref,
            external_id=contact_id,
        )

    def record_conversation_event(
        self,
        payload: dict,
        prospect_id: str,
        *,
        activity_type: str,
        activity_summary: str,
        metadata: dict | None = None,
    ) -> list[ToolExecutionResult]:
        contact_result = self.sync_contact_profile(payload, prospect_id)
        contact_id = contact_result.external_id
        enrichment_result = self.write_enrichment_fields(
            contact_id,
            self._enrichment_properties(payload),
            prospect_id,
        )
        activity_result = self.log_activity(
            contact_id,
            activity_type=activity_type,
            activity_summary=activity_summary,
            prospect_id=prospect_id,
            metadata=metadata,
        )
        return [contact_result, enrichment_result, activity_result]

    def upsert_contact(self, payload: dict, prospect_id: str) -> ToolExecutionResult:
        return self.sync_contact_profile(payload, prospect_id)


HubSpotClient = HubSpotMCPClient
hubspot_client = HubSpotMCPClient()
