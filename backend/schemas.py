"""
API response models. They mirror construction_hazards/schema.py OUTPUT_SCHEMA
exactly (same fields, same allowed severity and category values), so the
OpenAPI docs at /docs show the real output contract.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

from construction_hazards.schema import CATEGORIES, HAZARD_SCHEMA

SEVERITIES = HAZARD_SCHEMA["properties"]["hazards"]["items"]["properties"]["severity"]["enum"]

Severity = Literal[tuple(SEVERITIES)]
Category = Literal[tuple(CATEGORIES)]


class Hazard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    severity: Severity
    category: Category


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    hazards: list[Hazard]


class ProviderInfo(BaseModel):
    available: bool
    model: str
    effort: str | None = None


class HealthResponse(BaseModel):
    status: str
    providers: dict[str, ProviderInfo]


class CategoriesResponse(BaseModel):
    categories: list[str]
    severities: list[str]


class ErrorResponse(BaseModel):
    detail: str
