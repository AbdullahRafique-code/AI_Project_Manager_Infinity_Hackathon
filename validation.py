"""Shared extraction schema and deterministic checks; no database or UI access."""

from datetime import date
import math
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]
MODEL_CONFIG = ConfigDict(extra="forbid")


def _iso_date(value: object) -> date:
    """Accept only calendar dates written exactly as YYYY-MM-DD."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Use a date in YYYY-MM-DD format.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Provide a valid calendar date.") from exc


class TaskDraft(BaseModel):
    model_config = MODEL_CONFIG

    title: Text
    description: Text
    assigneeId: Text
    deadline: date
    estimatedHours: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("deadline", mode="before")
    @classmethod
    def _validate_deadline(cls, value: object) -> date:
        return _iso_date(value)

    @field_validator("estimatedHours", mode="before")
    @classmethod
    def _validate_hours(cls, value: object) -> float:
        if type(value) not in (int, float):
            raise ValueError("Estimated hours must be a number, not text or a boolean.")
        try:
            hours = float(value)
        except OverflowError as exc:
            raise ValueError("Estimated hours must be finite.") from exc
        if not math.isfinite(hours):
            raise ValueError("Estimated hours must be finite.")
        return hours


class ProjectDraft(BaseModel):
    model_config = MODEL_CONFIG

    name: Text
    clientName: Text
    description: Text
    managerId: Text
    deadline: date
    tasks: list[TaskDraft] = Field(min_length=1)

    @field_validator("deadline", mode="before")
    @classmethod
    def _validate_deadline(cls, value: object) -> date:
        return _iso_date(value)


class ExtractionDraft(BaseModel):
    model_config = MODEL_CONFIG

    projects: list[ProjectDraft] = Field(min_length=1)


def extraction_schema() -> dict:
    """Return the same JSON schema used to validate the model's response."""
    return ExtractionDraft.model_json_schema()


def validate_extraction(raw_json: str, directory: list[dict]) -> ExtractionDraft:
    """Validate the complete response before any database writes.

    Pydantic ValidationError identifies malformed fields. ValueError identifies
    directory/ownership/deadline violations. Nothing is silently repaired.
    Counts are intentionally unrestricted for genuinely different transcripts.
    """
    draft = ExtractionDraft.model_validate_json(raw_json)
    roles: dict[str, str] = {}
    for person in directory:
        user_id = person.get("id")
        role = person.get("role")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("The team directory contains a missing or invalid user ID.")
        if role not in ("ADMIN", "MANAGER", "AGENT"):
            raise ValueError(f"The team directory contains an invalid role for {user_id}.")
        if user_id in roles:
            raise ValueError(f"The team directory contains duplicate ID {user_id}.")
        roles[user_id] = role

    errors: list[str] = []
    for project_index, project in enumerate(draft.projects):
        project_path = f"projects[{project_index}]"
        if roles.get(project.managerId) != "MANAGER":
            errors.append(f"{project_path}.managerId: choose an existing MANAGER.")
        for task_index, task in enumerate(project.tasks):
            task_path = f"{project_path}.tasks[{task_index}]"
            if roles.get(task.assigneeId) != "AGENT":
                errors.append(f"{task_path}.assigneeId: choose an existing AGENT.")
            if task.deadline > project.deadline:
                errors.append(f"{task_path}.deadline: must be on or before the project deadline.")
    if errors:
        raise ValueError("\n".join(errors))
    return draft
