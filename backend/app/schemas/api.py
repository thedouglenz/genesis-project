from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


# --- Request schemas ---


class CreateConversationRequest(BaseModel):
    title: str | None = None


class SendMessageRequest(BaseModel):
    content: str


class LoginRequest(BaseModel):
    username: str
    password: str


# --- Response schemas ---


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str | None
    table_data: dict | None = None
    chart_data: dict | None = None
    pipeline_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: str


# --- Pipeline output schemas ---


class PlanOutput(BaseModel):
    reasoning: str
    query_strategy: str
    expected_answer_type: Literal["scalar", "dataset", "chart"]
    suggested_chart_type: Literal["bar", "line", "pie", "scatter"] | None = None
    tables_to_explore: list[str]
    conversation_name: str | None = None


class QueryExecuted(BaseModel):
    sql: str
    result_summary: str


class ExploreOutput(BaseModel):
    queries_executed: list[QueryExecuted]
    raw_data: Any
    exploration_notes: str
    schema_context: dict


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ChartData(BaseModel):
    type: Literal["bar", "line", "pie", "scatter"]
    title: str
    x_axis: str
    y_axis: str
    data: list[ChartDataPoint]


class TableData(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class AnswerOutput(BaseModel):
    text_answer: str
    table_data: TableData | None = None
    chart_data: ChartData | None = None


# --- Pipeline run response schemas ---


class PipelineStepResponse(BaseModel):
    id: uuid.UUID
    step_name: str
    step_order: int
    status: str
    attempts: int
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    steps: list[PipelineStepResponse]

    model_config = {"from_attributes": True}
