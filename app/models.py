# /app/models.py

from pydantic import BaseModel


class WorkItemRequest(BaseModel):
    project: str
    work_item_id: int


class PullRequestRequest(BaseModel):
    project: str
    pull_request_id: int


class ProjectListRequest(BaseModel):
    top: int | None = None
    skip: int | None = None
    continuation_token: str | None = None


class WiqlQueryRequest(BaseModel):
    project: str
    query: str
    top: int | None = None
    time_precision: bool | None = None
