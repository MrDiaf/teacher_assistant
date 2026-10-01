from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.assistant.errors import AssistantProposalLimitError, AssistantProposalStateError
from app.assistant.models import AssistantProposal
from app.assistant.proposals import (
    CalendarChangeProposal,
    CreateCalendarAction,
    CreateEventAction,
    DeleteEventAction,
    ProposalAction,
    UpdateCalendarAction,
    UpdateEventAction,
)
from app.calendar.public import (
    AssistantCalendarPort,
    CalendarReadOnlyError,
    CalendarSummary,
    EventSummary,
    InvalidRecurrenceError,
)
from app.core.errors import InvalidAssistantResponseError


@dataclass(frozen=True)
class PreparedProposal:
    actions: list[dict[str, Any]]
    baselines: list[dict[str, Any]]
    review_items: list[dict[str, Any]]
    warnings: list[str]
    affected_events: int


class ProposalValidator:
    def __init__(self, calendar: AssistantCalendarPort) -> None:
        self.calendar = calendar

    async def prepare(self, proposal: CalendarChangeProposal) -> PreparedProposal:
        try:
            prepared = await self._inspect(proposal, for_update=False)
            if prepared.affected_events > 10:
                raise AssistantProposalLimitError()
            return prepared
        except AssistantProposalLimitError:
            raise
        except (InvalidAssistantResponseError, InvalidRecurrenceError):
            raise
        except Exception as exc:
            raise InvalidAssistantResponseError(
                "The proposed calendar change could not be matched safely to current "
                "calendar data.",
                validation_stage="proposal_target_validation",
                validation_errors=[
                    {
                        "field": "proposal.actions",
                        "message": "A referenced calendar or event could not be safely validated.",
                        "type": type(exc).__name__,
                    }
                ],
            ) from exc

    async def revalidate(self, proposal: AssistantProposal) -> list[ProposalAction]:
        try:
            parsed = CalendarChangeProposal.model_validate(
                {
                    "type": "calendar_change",
                    "summary": proposal.summary,
                    "actions": proposal.actions,
                }
            )
            prepared = await self._inspect(parsed, for_update=True)
            if prepared.affected_events > 10:
                raise AssistantProposalLimitError()
        except Exception as exc:
            raise AssistantProposalStateError(
                "The proposal is no longer safe to execute. No calendar data changed."
            ) from exc

        if len(prepared.baselines) != len(proposal.baselines):
            raise AssistantProposalStateError(
                "The proposal targets changed after it was created. No calendar data changed."
            )
        for current, expected in zip(
            prepared.baselines, proposal.baselines, strict=True
        ):
            if current != expected:
                raise AssistantProposalStateError(
                    "A proposed calendar or event changed before confirmation. "
                    "No calendar data changed. Ask the assistant for a new proposal."
                )
        return list(parsed.actions)

    async def _inspect(
        self,
        proposal: CalendarChangeProposal,
        *,
        for_update: bool,
    ) -> PreparedProposal:
        actions: list[dict[str, Any]] = []
        baselines: list[dict[str, Any]] = []
        review_items: list[dict[str, Any]] = []
        warnings: list[str] = []
        affected_events = 0
        event_targets: set[uuid.UUID] = set()
        calendar_targets: set[uuid.UUID] = set()

        for action in proposal.actions:
            serialized = action.model_dump(mode="json", exclude_unset=True)
            actions.append(serialized)
            if isinstance(action, CreateCalendarAction):
                baselines.append({"operation": action.operation})
                review_items.append(
                    {
                        "operation": action.operation,
                        "title": f"Create calendar “{action.name}”",
                        "calendar_id": None,
                        "calendar_name": action.name,
                        "event_id": None,
                        "event_title": None,
                        "previous": None,
                        "proposed": {
                            "name": action.name,
                            "description": action.description,
                            "color": action.color,
                            "is_read_only": False,
                            "source_type": "local",
                        },
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                        "affected_events": 0,
                        "warnings": [],
                    }
                )
                continue

            if isinstance(action, UpdateCalendarAction):
                if action.calendar_id in calendar_targets:
                    raise InvalidAssistantResponseError(
                        "The proposal tried to update the same calendar more than once.",
                        validation_stage="proposal_safety_validation",
                        validation_errors=[
                            {
                                "field": "proposal.actions",
                                "message": "Duplicate calendar targets are not allowed.",
                                "type": "duplicate_calendar_target",
                            }
                        ],
                    )
                calendar_targets.add(action.calendar_id)
                calendar = await self.calendar.get_calendar(
                    action.calendar_id, lock_for_revalidation=for_update
                )
                self._ensure_writable(calendar)
                previous = self._calendar_state(calendar)
                proposed = dict(previous)
                proposed.update(action.changes.change_values())
                baselines.append(
                    {
                        "operation": action.operation,
                        "calendar_id": str(calendar.id),
                        "updated_at": calendar.updated_at.isoformat(),
                    }
                )
                review_items.append(
                    {
                        "operation": action.operation,
                        "title": f"Update calendar “{calendar.name}”",
                        "calendar_id": str(calendar.id),
                        "calendar_name": calendar.name,
                        "event_id": None,
                        "event_title": None,
                        "previous": previous,
                        "proposed": proposed,
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                        "affected_events": 0,
                        "warnings": [],
                    }
                )
                continue

            if isinstance(action, CreateEventAction):
                calendar = await self.calendar.get_calendar(
                    action.calendar_id, lock_for_revalidation=for_update
                )
                self._ensure_writable(calendar)
                self.calendar.validate_recurrence(action.event.recurrence_rule)
                event_count, action_warnings = self._affected_recurrence_count(
                    action.event.start_at, action.event.recurrence_rule
                )
                affected_events += event_count
                warnings.extend(action_warnings)
                baselines.append(
                    {
                        "operation": action.operation,
                        "calendar_id": str(calendar.id),
                    }
                )
                review_items.append(
                    {
                        "operation": action.operation,
                        "title": f"Create event “{action.event.title}”",
                        "calendar_id": str(calendar.id),
                        "calendar_name": calendar.name,
                        "event_id": None,
                        "event_title": action.event.title,
                        "previous": None,
                        "proposed": action.event.model_dump(mode="json"),
                        "recurrence_scope": (
                            "series" if action.event.recurrence_rule else None
                        ),
                        "occurrence_start_at": None,
                        "affected_events": event_count,
                        "warnings": action_warnings,
                    }
                )
                continue

            if action.event_id in event_targets:
                raise InvalidAssistantResponseError(
                    "The proposal tried to change the same event more than once.",
                    validation_stage="proposal_safety_validation",
                    validation_errors=[
                        {
                            "field": "proposal.actions",
                            "message": "Duplicate event targets are not allowed.",
                            "type": "duplicate_event_target",
                        }
                    ],
                )
            event_targets.add(action.event_id)
            event = await self.calendar.get_event(
                action.event_id, lock_for_revalidation=for_update
            )
            parent = (
                await self.calendar.get_event(
                    event.recurrence_parent_id,
                    lock_for_revalidation=for_update,
                )
                if event.recurrence_parent_id
                else event
            )
            calendar = await self.calendar.get_calendar(
                parent.calendar_id, lock_for_revalidation=for_update
            )
            self._ensure_writable(calendar)
            if action.calendar_id != parent.calendar_id:
                raise InvalidAssistantResponseError(
                    "The proposal's calendar ID did not match the targeted event.",
                    validation_stage="proposal_target_validation",
                    validation_errors=[
                        {
                            "field": "proposal.actions.calendar_id",
                            "message": "The event belongs to a different calendar.",
                            "type": "event_calendar_mismatch",
                        }
                    ],
                )
            is_recurring = parent.recurrence_rule is not None
            self._validate_recurrence_scope(action, is_recurring)

            if isinstance(action, UpdateEventAction):
                changes = action.changes.change_values()
                target_calendar_id = changes.get("calendar_id")
                if target_calendar_id is not None:
                    target_calendar = await self.calendar.get_calendar(
                        target_calendar_id, lock_for_revalidation=for_update
                    )
                    self._ensure_writable(target_calendar)
                previous = self._event_state(parent)
                proposed = dict(previous)
                proposed.update(action.changes.change_values(mode="json"))
                rule = proposed.get("recurrence_rule")
                self.calendar.validate_recurrence(rule)
                event_count, action_warnings = self._mutation_affected_count(
                    parent, action.recurrence_scope, rule
                )
                title = f"Update event “{parent.title}”"
            else:
                previous = self._event_state(parent)
                proposed = None
                event_count, action_warnings = self._mutation_affected_count(
                    parent, action.recurrence_scope, parent.recurrence_rule
                )
                title = f"Delete event “{parent.title}”"
                action_warnings = ["This deletion cannot be undone.", *action_warnings]

            affected_events += event_count
            warnings.extend(action_warnings)
            baselines.append(
                {
                    "operation": action.operation,
                    "calendar_id": str(calendar.id),
                    "event_id": str(event.id),
                    "event_updated_at": event.updated_at.isoformat(),
                    "series_parent_id": str(parent.id),
                    "series_parent_updated_at": parent.updated_at.isoformat(),
                }
            )
            review_items.append(
                {
                    "operation": action.operation,
                    "title": title,
                    "calendar_id": str(calendar.id),
                    "calendar_name": calendar.name,
                    "event_id": str(parent.id),
                    "event_title": parent.title,
                    "previous": previous,
                    "proposed": proposed,
                    "recurrence_scope": action.recurrence_scope,
                    "occurrence_start_at": (
                        action.occurrence_start_at.isoformat()
                        if action.occurrence_start_at
                        else None
                    ),
                    "affected_events": event_count,
                    "warnings": action_warnings,
                }
            )

        return PreparedProposal(
            actions=actions,
            baselines=baselines,
            review_items=review_items,
            warnings=list(dict.fromkeys(warnings)),
            affected_events=affected_events,
        )

    @staticmethod
    def _ensure_writable(calendar: CalendarSummary) -> None:
        if calendar.is_read_only:
            raise CalendarReadOnlyError()

    @staticmethod
    def _validate_recurrence_scope(
        action: UpdateEventAction | DeleteEventAction,
        is_recurring: bool,
    ) -> None:
        if not is_recurring:
            if action.recurrence_scope is not None or action.occurrence_start_at is not None:
                raise InvalidAssistantResponseError(
                    "The proposal supplied recurrence fields for an event that does not recur.",
                    validation_stage="recurrence_scope_validation",
                    validation_errors=[
                        {
                            "field": "proposal.actions.recurrence_scope",
                            "message": "Non-recurring events cannot use recurrence scope fields.",
                            "type": "unexpected_recurrence_scope",
                        }
                    ],
                )
            return
        if action.recurrence_scope is None:
            raise InvalidAssistantResponseError(
                "The proposal did not say whether one occurrence or the whole series "
                "should change.",
                validation_stage="recurrence_scope_validation",
                validation_errors=[
                    {
                        "field": "proposal.actions.recurrence_scope",
                        "message": "Recurring changes require occurrence or series scope.",
                        "type": "recurrence_scope_missing",
                    }
                ],
            )
        if action.recurrence_scope == "occurrence":
            if action.occurrence_start_at is None:
                raise InvalidAssistantResponseError(
                    "The proposal selected one occurrence but did not identify its start time.",
                    validation_stage="recurrence_scope_validation",
                    validation_errors=[
                        {
                            "field": "proposal.actions.occurrence_start_at",
                            "message": "Occurrence start time is required for one occurrence.",
                            "type": "occurrence_start_missing",
                        }
                    ],
                )
            if isinstance(action, UpdateEventAction):
                changed = action.changes.selected_fields()
                if "calendar_id" in changed or "recurrence_rule" in changed:
                    raise InvalidAssistantResponseError(
                        "A one-occurrence update tried to move calendars or change the "
                        "series rule.",
                        validation_stage="recurrence_scope_validation",
                        validation_errors=[
                            {
                                "field": "proposal.actions.changes",
                                "message": (
                                    "Calendar and recurrence-rule changes require "
                                    "full-series scope."
                                ),
                                "type": "occurrence_change_not_allowed",
                            }
                        ],
                    )
        elif action.occurrence_start_at is not None:
            raise InvalidAssistantResponseError(
                "The proposal supplied an occurrence start time for a full-series change.",
                validation_stage="recurrence_scope_validation",
                validation_errors=[
                    {
                        "field": "proposal.actions.occurrence_start_at",
                        "message": "Full-series changes must not identify one occurrence.",
                        "type": "unexpected_occurrence_start",
                    }
                ],
            )

    @staticmethod
    def _calendar_state(calendar: CalendarSummary) -> dict[str, Any]:
        return {
            "name": calendar.name,
            "description": calendar.description,
            "color": calendar.color,
        }

    @staticmethod
    def _event_state(event: EventSummary) -> dict[str, Any]:
        return {
            "calendar_id": str(event.calendar_id),
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "start_at": event.start_at.isoformat(),
            "end_at": event.end_at.isoformat(),
            "all_day": event.all_day,
            "timezone": event.timezone,
            "recurrence_rule": event.recurrence_rule,
            "status": event.status.value,
        }

    def _mutation_affected_count(
        self,
        event: EventSummary,
        scope: str | None,
        recurrence_rule: str | None,
    ) -> tuple[int, list[str]]:
        if scope != "series":
            return 1, []
        return self._affected_recurrence_count(event.start_at, recurrence_rule)

    @staticmethod
    def _affected_recurrence_count(
        _start_at: datetime, recurrence_rule: str | None
    ) -> tuple[int, list[str]]:
        if not recurrence_rule:
            return 1, []
        parts = dict(
            segment.split("=", 1)
            for segment in recurrence_rule.split(";")
            if "=" in segment
        )
        if "COUNT" in parts:
            try:
                return max(1, min(int(parts["COUNT"]), 999)), []
            except ValueError:
                pass
        return (
            1,
            [
                "This is a recurring series; the affected-event count is a minimum "
                "because the series has no fixed occurrence count."
            ],
        )
