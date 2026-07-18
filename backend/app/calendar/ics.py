from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.calendar.models import EventStatus
from app.core.errors import IcsFileTooLargeError, InvalidIcsError

MAX_ICS_BYTES = 5 * 1024 * 1024
MAX_ICS_EVENTS = 5000
DEFAULT_TIMEZONE = "Europe/Stockholm"
DATE_PATTERN = re.compile(r"^\d{8}$")
DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)
UTC_UNTIL_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
ALLOWED_RECURRENCE_PARTS = {"FREQ", "INTERVAL", "COUNT", "UNTIL"}
ALLOWED_RECURRENCE_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY"}


@dataclass(frozen=True)
class IcsIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class IcsProperty:
    value: str
    parameters: dict[str, str]


@dataclass
class ParsedIcsEvent:
    index: int
    uid: str | None
    title: str
    description: str | None
    location: str | None
    start_at: datetime | None
    end_at: datetime | None
    all_day: bool
    timezone: str
    recurrence_rule: str | None
    status: EventStatus
    issues: list[IcsIssue] = field(default_factory=list)

    @property
    def is_importable(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


@dataclass(frozen=True)
class ParsedIcsCalendar:
    file_name: str
    suggested_calendar_name: str
    events: list[ParsedIcsEvent]


def _unfold_lines(text: str) -> list[str]:
    unfolded: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _parse_property(line: str) -> tuple[str, IcsProperty] | None:
    if ":" not in line:
        return None
    descriptor, value = line.split(":", 1)
    segments = descriptor.split(";")
    name = segments[0].upper()
    parameters: dict[str, str] = {}
    for segment in segments[1:]:
        key, separator, parameter_value = segment.partition("=")
        if separator:
            parameters[key.upper()] = parameter_value.strip('"')
    return name, IcsProperty(value=value, parameters=parameters)


def _unescape_text(value: str) -> str:
    return (
        value.replace("\\N", "\n")
        .replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f'Unknown timezone "{name}".') from exc


def _parse_temporal(
    prop: IcsProperty,
    *,
    fallback_timezone: str = DEFAULT_TIMEZONE,
) -> tuple[datetime, bool, str]:
    value = prop.value.strip()
    is_date = prop.parameters.get("VALUE", "").upper() == "DATE" or bool(
        DATE_PATTERN.fullmatch(value)
    )
    timezone_name = prop.parameters.get("TZID", fallback_timezone)
    if is_date:
        parsed_date = datetime.strptime(value, "%Y%m%d").date()
        return (
            datetime.combine(parsed_date, time.min, tzinfo=_timezone(timezone_name)),
            True,
            timezone_name,
        )

    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC), False, "UTC"
    if re.fullmatch(r"\d{8}T\d{6}[+-]\d{4}", value):
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%S%z")
        return (
            parsed,
            False,
            prop.parameters.get("TZID", str(parsed.tzinfo)),
        )
    for value_format in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            parsed = datetime.strptime(value, value_format)
            return parsed.replace(tzinfo=_timezone(timezone_name)), False, timezone_name
        except ValueError:
            continue
    raise ValueError("Date-time must use a supported ICS date or date-time format.")


def _parse_duration(value: str) -> timedelta:
    match = DURATION_PATTERN.fullmatch(value.strip().upper())
    if not match or not any(match.groupdict().values()):
        raise ValueError("DURATION must use a supported positive ISO 8601 duration.")
    duration = timedelta(
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )
    if duration <= timedelta(0):
        raise ValueError("DURATION must be greater than zero.")
    return duration


def _normalize_recurrence(value: str) -> str:
    parts: dict[str, str] = {}
    for segment in value.upper().split(";"):
        key, separator, part_value = segment.partition("=")
        if not separator or not part_value or key in parts or key not in ALLOWED_RECURRENCE_PARTS:
            raise ValueError("Only simple daily, weekly, or monthly RRULE values are supported.")
        parts[key] = part_value
    if parts.get("FREQ") not in ALLOWED_RECURRENCE_FREQUENCIES:
        raise ValueError("Only daily, weekly, or monthly recurrence is supported.")
    for key, maximum in (("INTERVAL", 365), ("COUNT", 999)):
        if key in parts:
            if not parts[key].isdigit() or not 1 <= int(parts[key]) <= maximum:
                raise ValueError(f"RRULE {key} is outside the supported range.")
    if "UNTIL" in parts and not UTC_UNTIL_PATTERN.fullmatch(parts["UNTIL"]):
        raise ValueError("RRULE UNTIL must be a UTC date-time ending in Z.")
    return ";".join(f"{key}={part_value}" for key, part_value in parts.items())


def _first(properties: dict[str, list[IcsProperty]], name: str) -> IcsProperty | None:
    values = properties.get(name)
    return values[0] if values else None


def _issue(issues: list[IcsIssue], severity: str, message: str) -> None:
    issues.append(IcsIssue(severity=severity, message=message))


def _build_event(
    index: int,
    properties: dict[str, list[IcsProperty]],
    line_issues: list[IcsIssue],
    seen_uids: set[str],
) -> ParsedIcsEvent:
    issues = list(line_issues)
    uid_prop = _first(properties, "UID")
    uid = uid_prop.value.strip() if uid_prop and uid_prop.value.strip() else None
    if uid is None:
        _issue(
            issues,
            "warning",
            "This event has no UID, so duplicate detection is not available.",
        )
    elif len(uid) > 500:
        _issue(issues, "error", "UID exceeds the supported 500-character limit.")
    elif uid in seen_uids:
        _issue(issues, "error", "A previous event in this file uses the same UID.")
    else:
        seen_uids.add(uid)

    title_prop = _first(properties, "SUMMARY")
    title = _unescape_text(title_prop.value).strip() if title_prop else ""
    if not title:
        title = "Untitled event"
        _issue(issues, "warning", "Missing SUMMARY; the event will be named Untitled event.")
    if len(title) > 240:
        _issue(issues, "error", "SUMMARY exceeds the supported 240-character limit.")

    description_prop = _first(properties, "DESCRIPTION")
    description = _unescape_text(description_prop.value) if description_prop else None
    location_prop = _first(properties, "LOCATION")
    location = _unescape_text(location_prop.value) if location_prop else None
    if location and len(location) > 500:
        _issue(issues, "error", "LOCATION exceeds the supported 500-character limit.")

    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day = False
    timezone_name = DEFAULT_TIMEZONE
    start_prop = _first(properties, "DTSTART")
    if start_prop is None:
        _issue(issues, "error", "Missing required DTSTART.")
    else:
        try:
            start_at, all_day, timezone_name = _parse_temporal(start_prop)
        except ValueError as exc:
            _issue(issues, "error", f"Invalid DTSTART: {exc}")

    end_prop = _first(properties, "DTEND")
    duration_prop = _first(properties, "DURATION")
    if start_at is not None:
        if end_prop is not None:
            try:
                end_at, end_is_date, _end_timezone = _parse_temporal(
                    end_prop, fallback_timezone=timezone_name
                )
                if end_is_date != all_day:
                    _issue(issues, "error", "DTSTART and DTEND must use the same value type.")
            except ValueError as exc:
                _issue(issues, "error", f"Invalid DTEND: {exc}")
        elif duration_prop is not None:
            try:
                end_at = start_at + _parse_duration(duration_prop.value)
            except ValueError as exc:
                _issue(issues, "error", str(exc))
        elif all_day:
            end_at = start_at + timedelta(days=1)
            _issue(issues, "warning", "Missing DTEND; a one-day duration will be used.")
        else:
            _issue(issues, "error", "Timed events require DTEND or DURATION.")
    if start_at is not None and end_at is not None and end_at <= start_at:
        _issue(issues, "error", "DTEND must be later than DTSTART.")

    recurrence_rule: str | None = None
    recurrence_prop = _first(properties, "RRULE")
    if recurrence_prop is not None:
        try:
            recurrence_rule = _normalize_recurrence(recurrence_prop.value)
        except ValueError as exc:
            _issue(issues, "error", str(exc))
    for unsupported in ("RECURRENCE-ID", "RDATE", "EXDATE"):
        if unsupported in properties:
            _issue(
                issues,
                "error",
                f"{unsupported} recurrence exceptions are not supported in M4.",
            )

    status = EventStatus.CONFIRMED
    status_prop = _first(properties, "STATUS")
    if status_prop:
        normalized_status = status_prop.value.strip().lower()
        try:
            status = EventStatus(normalized_status)
        except ValueError:
            _issue(
                issues,
                "warning",
                f'Unsupported STATUS "{status_prop.value}"; confirmed will be used.',
            )

    return ParsedIcsEvent(
        index=index,
        uid=uid,
        title=title,
        description=description,
        location=location,
        start_at=start_at,
        end_at=end_at,
        all_day=all_day,
        timezone=timezone_name,
        recurrence_rule=recurrence_rule,
        status=status,
        issues=issues,
    )


def parse_ics(content: bytes, file_name: str) -> ParsedIcsCalendar:
    if len(content) > MAX_ICS_BYTES:
        raise IcsFileTooLargeError()
    safe_file_name = Path(file_name or "calendar.ics").name
    if not safe_file_name.lower().endswith(".ics"):
        raise InvalidIcsError("Choose a file with the .ics extension.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidIcsError("The ICS file must use UTF-8 text encoding.") from exc

    lines = _unfold_lines(text)
    if not any(line.strip().upper() == "BEGIN:VCALENDAR" for line in lines) or not any(
        line.strip().upper() == "END:VCALENDAR" for line in lines
    ):
        raise InvalidIcsError("The file does not contain a complete VCALENDAR block.")

    calendar_name: str | None = None
    raw_events: list[tuple[dict[str, list[IcsProperty]], list[IcsIssue]]] = []
    current: dict[str, list[IcsProperty]] | None = None
    current_issues: list[IcsIssue] = []
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper == "BEGIN:VEVENT":
            if current is not None:
                raise InvalidIcsError("Nested VEVENT blocks are not supported.")
            current = {}
            current_issues = []
            continue
        if upper == "END:VEVENT":
            if current is None:
                raise InvalidIcsError("An END:VEVENT appears without a matching BEGIN:VEVENT.")
            raw_events.append((current, current_issues))
            current = None
            current_issues = []
            if len(raw_events) > MAX_ICS_EVENTS:
                raise InvalidIcsError("The ICS file contains more than 5,000 events.")
            continue
        parsed = _parse_property(stripped) if stripped else None
        if current is not None:
            if parsed is None:
                if stripped:
                    _issue(current_issues, "error", "An event property line is malformed.")
                continue
            name, prop = parsed
            current.setdefault(name, []).append(prop)
        elif parsed and parsed[0] == "X-WR-CALNAME":
            calendar_name = _unescape_text(parsed[1].value).strip() or None

    if current is not None:
        raise InvalidIcsError("A VEVENT block is missing END:VEVENT.")
    if not raw_events:
        raise InvalidIcsError("The ICS file contains no VEVENT entries.")

    seen_uids: set[str] = set()
    events = [
        _build_event(index, properties, issues, seen_uids)
        for index, (properties, issues) in enumerate(raw_events, start=1)
    ]
    suggested_name = (calendar_name or Path(safe_file_name).stem or "Imported calendar")[:120]
    return ParsedIcsCalendar(
        file_name=safe_file_name,
        suggested_calendar_name=suggested_name,
        events=events,
    )
