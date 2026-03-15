#!/bin/bash

docker build -t azure-devops-mcp:latest .

docker run -d --name azure-devops-mcp \
  -p 8000:8000 \
  --restart unless-stopped \
  --env-file ./.env \
  azure-devops-mcp:latest