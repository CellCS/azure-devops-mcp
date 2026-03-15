# AGENTS.md

Repository instructions for agentic coding assistants working in `azure-devops-mcp`.

## 1) Project Facts
- Language/runtime: Python 3.13+
- Stack: FastAPI, FastMCP, Uvicorn, Requests, Pydantic Settings
- Package/dependency manager: `uv`
- Main entrypoint: `main.py`
- Core modules: `libs/config.py`, `libs/devops_client.py`, `libs/models.py`
- Purpose: read-only Azure DevOps MCP server

## 2) Rule Files (Cursor/Copilot)
- `.cursorrules`: not found
- `.cursor/rules/`: not found
- `.github/copilot-instructions.md`: not found
- If these files are added later, treat them as high-priority instructions.

## 3) Environment and Secrets
- Required env vars: `AZURE_ORG`, `AZURE_PAT`, `MCP_BEARER_TOKENS`
- Optional env var: `MCP_HTTP_PATH` (defaults to `/devops-mcp`)
- Use `.env.example` for placeholders only.
- Never commit real tokens, PATs, private keys, or production hostnames.
- Keep `.env` local and ignored.

## 4) Setup Commands
Install project dependencies:
```bash
uv sync
```
Install with dev tools:
```bash
uv sync --dev
```

## 5) Build / Run Commands
Run API locally:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```
Quick health check:
```bash
curl http://127.0.0.1:8000/healthz
```
Docker build:
```bash
docker build -t azure-devops-mcp:latest .
```
Docker run (example placeholders):
```bash
docker run -d --name azure-devops-mcp -p 8000:8000 \
  -e AZURE_ORG=your-organization-name \
  -e AZURE_PAT=your-personal-access-token \
  -e MCP_BEARER_TOKENS=your-mcp-token-1,your-mcp-token-2 \
  azure-devops-mcp:latest
```

## 6) Lint / Check / Security Commands
There is no dedicated formatter/linter config yet in `pyproject.toml`.
Use the following project-accepted checks.
Syntax/build sanity:
```bash
uv run python -m compileall main.py libs
```
Static security scan:
```bash
uv run bandit -r libs main.py
```
Dependency vulnerability scan:
```bash
uv run pip-audit
```
Full security pipeline:
```bash
bash security-scan.sh
```

## 7) Test Commands (Including Single Test)
Current state: no committed automated test suite yet.
When adding tests, standardize on `pytest` and use:
Run full suite:
```bash
uv run pytest
```
Run a single test file:
```bash
uv run pytest tests/test_<module>.py
```
Run one test function:
```bash
uv run pytest tests/test_<module>.py::test_<name>
```
Run one class test method:
```bash
uv run pytest tests/test_<module>.py::Test<ClassName>::test_<name>
```

## 8) Code Style: Imports and Structure
- Import grouping order: stdlib, third-party, local modules.
- Use explicit imports; avoid wildcard imports.
- Preserve existing import patterns:
  - `main.py` imports via `from libs...`
  - modules under `libs/` use relative imports where already used.
- Keep request schemas in `libs/models.py`.
- Keep Azure DevOps HTTP logic in `libs/devops_client.py`.
- Keep transport/middleware/tool registration in `main.py`.

## 9) Code Style: Formatting and Types
- Follow PEP 8 with 4-space indentation.
- Keep code readable; avoid overly long lines.
- Prefer modern typing (`str | None`, `list[int]`, `dict[str, Any]`).
- Add type hints to all new public functions/methods.
- Use Pydantic `BaseModel` for MCP request payloads.
- Keep models strict and minimal; avoid extra unused fields.

## 10) Naming Conventions
- Variables/functions/methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Use domain names already present in repo.
- Prefer names like `project`, `work_item_id`, `pull_request_id`, `continuation_token`.

## 11) Error Handling and API Behavior
- Always set request timeouts for outbound HTTP calls.
- Always call `response.raise_for_status()` on Azure DevOps responses.
- In MCP tool handlers, wrap failures with `ToolError`.
- Preserve traceability using `raise ... from e`.
- Keep successful responses JSON-serializable and predictable.
- Prefer non-breaking response shape changes.

## 12) Security and Open-Source Hygiene
- Never hardcode credentials or secrets.
- Do not print PATs or bearer tokens in logs/errors/docs.
- Keep examples sanitized with placeholders.
- URL-encode project references before placing in path segments.
- Keep `uv.lock` versioned for reproducible application installs.
- Re-scan for secrets before commits intended for open source.

## 13) Expected Change Workflow for Agents
- Make minimal, focused edits only.
- Avoid opportunistic refactors unless requested.
- Update `README.md` when behavior/env/tooling changes.
- If adding a tool, add a usage example prompt in `README.md`.
- Before handoff, run at least:
  - `uv run python -m compileall main.py libs`
  - relevant security/test command(s) for touched areas.
