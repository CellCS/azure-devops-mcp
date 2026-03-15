#!/bin/bash

docker build -t azure-devops-mcp:latest .

docker run -d --name azure-devops-mcp \
  -p 8000:8000 \
  --restart unless-stopped \
  -e AZURE_ORG=your-organization-name \
  -e AZURE_PAT=your-personal-access-token \
  -e MCP_BEARER_TOKENS=your-mcp-token-1,your-mcp-token-2 \
  azure-devops-mcp:latest
