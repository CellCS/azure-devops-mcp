# Deployment Controls Checklist

Service: azure-devops-mcp  
Framework: FastAPI + FastMCP (Python 3.13)
Deployment Model: Docker container behind reverse proxy
Scan Date: 2026-03-15  

---

# 1. Dependency Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Dependency vulnerability scan | Python dependencies scanned with pip-audit | PASS | 01-pip-audit.txt |
| Static code scan | Source code scanned using Bandit | PASS | 02-bandit.txt |
| Secret scanning | Repository scanned for leaked credentials | PASS | 03-gitleaks_output.txt |

---

# 2. Container Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Container vulnerability scan (87) | Image scanned with Trivy (no critical vulnerabilities) | PASS | 05-trivy.txt |
| SBOM generation | Software Bill of Materials generated | PASS | 06-sbom-cyclonedx.json |

---

# 3. Transport Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| TLS enforcement | HTTPS required via reverse proxy | MANUAL | Nginx / gateway configuration |
| TLS certificate | Valid certificate installed | MANUAL | TLS certificate validation |

---

# 4. Authentication and Authorization

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| MCP authentication | MCP_BEARER_TOKENS configured | MANUAL | Deployment environment configuration |
| Azure DevOps PAT | PAT configured with read-only scopes | MANUAL | Azure DevOps configuration |

---

# 5. Network Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Container isolation | Service runs on private Docker network | MANUAL | Docker compose configuration |
| Limited exposed ports | Only reverse proxy exposed publicly | MANUAL | Firewall/security group rules |

---

# 6. Logging and Monitoring

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Access logging | API access logs enabled | MANUAL | Reverse proxy logs |
| Monitoring | Alerts configured for unusual traffic | MANUAL | Monitoring dashboard |

---

# Evidence Artifacts

security-scan-results/

- 01-pip-audit.txt
- 02-bandit.txt
- 03-gitleaks_output.txt
- 04-gitleaks.json
- 05-trivy.txt
- 06-sbom-cyclonedx.json

---

# Summary

| Scan | Status |
|---|---|
| Dependency Scan | PASS |
| Static Security Scan | PASS |
| Secret Scan | PASS |
| Container Scan | PASS |
| SBOM | PASS |

