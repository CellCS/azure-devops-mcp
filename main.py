from functools import lru_cache

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.devops_client import AzureDevOpsClient
from app.config import get_configured_mcp_tokens, get_mcp_http_path
from app.models import (
    ProjectListRequest,
    PullRequestRequest,
    WiqlQueryRequest,
    WorkItemRequest,
)

mcp = FastMCP("Azure DevOps MCP")
MCP_HTTP_PATH = get_mcp_http_path()
app = mcp.http_app(path=MCP_HTTP_PATH, transport="http")


@app.middleware("http")
async def require_bearer_token(request: Request, call_next):
    path = request.url.path

    if path == "/healthz":
        return await call_next(request)

    if path.startswith("/.well-known/"):
        return await call_next(request)

    if path == "/register":
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    configured_tokens = get_configured_mcp_tokens()
    if not configured_tokens:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")

    if scheme.lower() != "bearer" or token.strip() not in configured_tokens:
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Unauthorized. Provide a valid Bearer token in the Authorization header."
            },
        )

    return await call_next(request)


@app.route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@lru_cache
def get_client() -> AzureDevOpsClient:
    return AzureDevOpsClient()


@mcp.tool()
def get_projects_list(request: ProjectListRequest | None = None):
    """Retrieve Azure DevOps projects for the configured organization."""
    request = request or ProjectListRequest()
    try:
        return get_client().get_projects(
            top=request.top,
            skip=request.skip,
            continuation_token=request.continuation_token,
        )
    except Exception as e:
        raise ToolError(f"Failed to fetch project list: {e}") from e


@mcp.tool()
def get_work_item_content(request: WorkItemRequest):
    """Retrieve full details for a specific work item ID from azure devops."""
    try:
        return get_client().get_work_item(request.project, request.work_item_id)
    except Exception as e:
        raise ToolError(f"Failed to fetch work item content: {e}") from e


@mcp.tool()
def query_work_items_by_wiql(request: WiqlQueryRequest):
    """
    Run Azure DevOps Query By WIQL for a project.

    WIQL authoring tips (based on Azure DevOps REST API docs):
    - Use `FROM WorkItems` for normal item lists.
    - Include fields in `SELECT` that users need in tabular results
      (commonly: `System.Id`, `System.Title`, `System.State`, `System.AssignedTo`).
    - Scope by project with `WHERE [System.TeamProject] = @project`.
    - Common filters: work item type, state, assignee, area path, iteration path.
    - Use `ORDER BY` to produce stable and user-friendly output.
    - `top` limits result count (`$top` query parameter).
    - `time_precision` controls `timePrecision` behavior for date/time comparisons.

    Practical WIQL templates:
    1) Active bugs assigned to current user:
       SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
       FROM WorkItems
       WHERE [System.TeamProject] = @project
         AND [System.WorkItemType] = 'Bug'
         AND [System.State] <> 'Closed'
         AND [System.AssignedTo] = @Me
       ORDER BY [System.ChangedDate] DESC

    2) My active tasks in current iteration:
       SELECT [System.Id], [System.Title], [System.State], [System.IterationPath]
       FROM WorkItems
       WHERE [System.TeamProject] = @project
         AND [System.WorkItemType] = 'Task'
         AND [System.State] <> 'Done'
         AND [System.AssignedTo] = @Me
         AND [System.IterationPath] UNDER @CurrentIteration
       ORDER BY [System.ChangedDate] DESC

    3) Recently created user stories:
       SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate]
       FROM WorkItems
       WHERE [System.TeamProject] = @project
         AND [System.WorkItemType] = 'User Story'
       ORDER BY [System.CreatedDate] DESC

    Note: WIQL results usually return references (IDs/URLs/columns). Fetch full
    item details with `get_work_item_content` when richer fields are needed.
    """
    try:
        return get_client().query_by_wiql(
            project=request.project,
            query=request.query,
            top=request.top,
            time_precision=request.time_precision,
        )
    except Exception as e:
        raise ToolError(f"Failed to run WIQL query: {e}") from e


@mcp.tool()
def get_related_work_item_info(request: WorkItemRequest):
    """
    Retrieve related work items for a given work item ID from azure devops.
    """
    try:
        return get_client().get_related_work_items(
            request.project, request.work_item_id
        )

    except Exception as e:
        raise ToolError(f"Failed to fetch related work item info: {e}") from e


@mcp.tool()
def get_test_workitem_steps(request: WorkItemRequest):
    """Retrieve decoded test steps for a Test Case work item ID."""
    try:
        return get_client().get_test_workitem_steps(
            request.project, request.work_item_id
        )
    except Exception as e:
        raise ToolError(f"Failed to fetch test work item steps: {e}") from e


@mcp.tool()
def get_pull_request_content(request: PullRequestRequest):
    """Retrieve full details for a specific pull request ID from azure devops."""
    try:
        return get_client().get_pull_request_by_id(
            request.project, request.pull_request_id
        )
    except Exception as e:
        raise ToolError(f"Failed to fetch pull request content: {e}") from e
