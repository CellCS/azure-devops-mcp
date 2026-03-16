# Azure DevOps MCP Service

`azure-devops-mcp` is a Model Context Protocol (MCP) service built with FastAPI and FastMCP in Python.
It exposes Azure DevOps work item operations as reusable tools for AI agents and developer tooling.

## Purpose

This service provides:

- Centralized authentication using Azure DevOps PAT
- Reusable MCP tools
- A clean API layer over Azure DevOps REST endpoints

## Current capabilities

Implemented today:

- `get_projects_list`: list projects in the configured Azure DevOps organization
- `get_work_item_content`: retrieve a work item by ID in a provided project
- `query_work_items_by_wiql`: run WIQL query by project
- `get_related_work_item_info`: retrieve related work items and relation metadata in a provided project
- `get_test_workitem_steps`: decode and return Test Case steps in a provided project
- `get_pull_request_content`: retrieve a pull request by ID in a provided project

## Architecture overview

Before connecting an MCP client:

1. Copy env template:

```bash
cp .env.example .env
```

2. Edit `.env` and set at least:

   - `AZURE_ORG` (your Azure DevOps organization name)
   - `AZURE_PAT` (your Azure DevOps personal access token)
   - `MCP_BEARER_TOKENS` (token used by MCP clients)

3. Build the Docker image and start the MCP container:

```bash
sh deploy-container.sh
```

4. Verify the service is up:

```bash
curl http://127.0.0.1:8000/healthz
```

5. If the health check returns `{"status":"ok"}`, configure your MCP client to connect.

For remote/VPS deployment, run the container behind an HTTPS reverse proxy and keep the service on a private network.

The MCP server:

- Manages authentication
- Calls Azure DevOps REST APIs
- Returns structured JSON responses

`azure-devops-mcp` provides a single MCP endpoint that brokers read-only Azure DevOps access for AI clients.

```text
MCP Client (OpenCode / Copilot / Open WebUI)
        |
HTTPS + Bearer token
        |
Reverse Proxy (TLS termination)
        |
Private Docker network (internal service traffic)
        |
Azure DevOps MCP (FastAPI + FastMCP)
        |
Azure DevOps REST API (PAT auth)
```

The service is intentionally read-only and does not expose write/update endpoints.

## MCP Configuration

For **OpenCode**

```json
"azure-devops-mcp": {
    "type": "remote",
    "url": "http://127.0.0.1:8000/azure-devops-mcp",
    "oauth": false,
    "headers": {
        "Authorization": "Bearer your-mcp-token-1"
    }
}
```

For **Cline**:

```json
"azure-devops-mcp": {
    "autoApprove": [],
    "disabled": false,
    "timeout": 60,
    "type": "streamableHttp",
    "url": "http://127.0.0.1:8000/azure-devops-mcp",
    "headers": {
    "Authorization": "Bearer your-mcp-token-1"
    }
}
```

## Tech stack

- Python 3.13+
- FastAPI
- FastMCP
- Pydantic Settings
- Requests

## Project structure

```text
azure-devops-mcp/
|- app/
|  |- config.py          # Environment configuration
|  |- devops_client.py   # Azure DevOps REST client
|  |- models.py          # Pydantic request models
|- main.py               # FastAPI + FastMCP entrypoint
|- pyproject.toml
|- uv.lock
|- .env.example
`- README.md
```

## Security model

- `MCP_BEARER_TOKENS` is required; startup fails if it is missing or empty
- MCP requests require `Authorization: Bearer <token>`
- Azure DevOps credentials are read from environment variables (`app/config.py`)
- `AZURE_PROJECT`/`AZURE_PROJECT_ID` are not required; each tool call includes a `project`
- Required Azure DevOps env vars are `AZURE_ORG` and `AZURE_PAT`
- External access is expected through HTTPS at the reverse proxy
- The service itself only performs read-only Azure DevOps operations

## Deployment controls checklist

Latest generated evidence is under `security-scan-results/`.

| Control | Requirement | Result | Evidence |
|---|---|---|---|
| Dependency vulnerability scan | Python dependencies scanned with pip-audit | PASS | [`01-pip-audit.txt`](security-scan-results/01-pip-audit.txt) |
| Static code scan | Source code scanned using Bandit | PASS | [`02-bandit.txt`](security-scan-results/02-bandit.txt) |
| Secret scanning | Repository scanned for leaked credentials | PASS | [`03-gitleaks_output.txt`](security-scan-results/03-gitleaks_output.txt), [`04-gitleaks.json`](security-scan-results/04-gitleaks.json) |
| Container vulnerability scan | Image scanned with Trivy (critical vulnerabilities = 0) | PASS | [`05-trivy.txt`](security-scan-results/05-trivy.txt) |
| SBOM generation | CycloneDX SBOM generated from container image | PASS | [`06-sbom-cyclonedx.json`](security-scan-results/06-sbom-cyclonedx.json) |
| Full checklist report | Deployment controls summary for this run | PASS | [`security_checklist.md`](security-scan-results/security_checklist.md) |

## Example chat prompts

Use these prompts when testing from an MCP-enabled chat client.
Run the project-list prompt first, then reuse the exact returned project name in later prompts.

- `List all projects in this Azure DevOps organization.`
- `Get work item 1234 details and summary in project "MyProject".`
- `Run WIQL in project "MyProject" to list active Bugs assigned to me.`
- `Get work item 1234 and its related work items in project "MyProject".`
- `List all test steps for test case work item 13083 in project "MyProject".`
- `Get pull request 1234 details in project "MyProject".`
- `List top 10 active tasks in project "MyProject" ordered by priority and created date using WIQL.`

## WIQL request example

Use `query_work_items_by_wiql` with a request body like this:

```json
{
  "project": "MyProject",
  "query": "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] = 'Bug' AND [System.State] <> 'Closed' ORDER BY [System.ChangedDate] DESC",
  "top": 20,
  "time_precision": false
}
```

Notes:

- `project` must match an existing project name from `get_projects_list`.
- `query` is standard WIQL text.
- `top` and `time_precision` are optional.

## WIQL prompt-to-query mapping

Use these patterns when converting user intent into a WIQL query string.

1) User asks: "List active bugs assigned to me"

```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.WorkItemType] = 'Bug'
  AND [System.State] <> 'Closed'
  AND [System.AssignedTo] = @Me
ORDER BY [System.ChangedDate] DESC
```

2) User asks: "Show my active tasks in current sprint"

```sql
SELECT [System.Id], [System.Title], [System.State], [System.IterationPath]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.WorkItemType] = 'Task'
  AND [System.State] <> 'Done'
  AND [System.AssignedTo] = @Me
  AND [System.IterationPath] UNDER @CurrentIteration
ORDER BY [System.ChangedDate] DESC
```

3) User asks: "Show recently created user stories"

```sql
SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.WorkItemType] = 'User Story'
ORDER BY [System.CreatedDate] DESC
```

Guidelines:

- Always include `[System.TeamProject] = @project`.
- Use explicit `ORDER BY` for deterministic output.
- Keep `SELECT` small (ID/title/state + one or two extra fields).
- Use `top` to cap result size for chat responses.
- If full work item content is needed, query IDs first, then call `get_work_item_content`.

## Security Scan Summary

Status values below are examples from a successful run. Always check the latest generated report before release.

| Scan | Status |
|---|---|
| Dependency Scan | PASS |
| Static Security Scan | PASS |
| Secret Scan | PASS |
| Container Scan | PASS |
| SBOM | PASS |

Check [Security Scan](security-scan-results/security_checklist.md)

## References

[Azure DevOps REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/?view=azure-devops-rest-7.1)
[Azure DevOps Core Projects API](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/list?view=azure-devops-rest-7.1&tabs=HTTP)
[Azure DevOps WIQL Query By WIQL API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/wiql/query-by-wiql?view=azure-devops-rest-7.1&tabs=HTTP)
[microsoft azure-devops-mcp](https://github.com/microsoft/azure-devops-mcp)
