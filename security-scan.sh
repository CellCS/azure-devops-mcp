#!/bin/bash

# all scan results will be stored in the security-scan-results directory
rm -fr ./security-scan-results
mkdir -p ./security-scan-results

uv run pip-audit 2>&1 | tee ./security-scan-results/01-pip-audit.txt


uv run bandit -r app main.py 2>&1 | tee ./security-scan-results/02-bandit.txt


docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest detect --source /repo --report-format json --report-path /repo/security-scan-results/04-gitleaks.json 2>&1 | tee ./security-scan-results/03-gitleaks_output.txt

set -o pipefail
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image \
  --severity CRITICAL \
  --exit-code 1 \
  azure-devops-mcp:latest 2>&1 | tee ./security-scan-results/05-trivy.txt

TRIVY_EXIT_CODE=${PIPESTATUS[0]}

TRIVY_PACKAGE_COUNT=$(awk 'match($0, /pkg_num=[0-9]+/) { print substr($0, RSTART + 8, RLENGTH - 8); exit }' ./security-scan-results/05-trivy.txt)
if [ -z "$TRIVY_PACKAGE_COUNT" ]; then
    TRIVY_PACKAGE_COUNT="N/A"
fi


docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd):/repo" \
  anchore/syft:latest \
  azure-devops-mcp:latest -o cyclonedx-json \
  > ./security-scan-results/06-sbom-cyclonedx.json

# ------------------------------------------------------------
# Generate Deployment Controls Checklist Report
# ------------------------------------------------------------

CHECKLIST_FILE="./security-scan-results/security_checklist.md"
DATE=$(date "+%Y-%m-%d")

echo "Generating deployment controls checklist..."

# Default statuses
PIP_AUDIT_STATUS="FAIL"
BANDIT_STATUS="FAIL"
GITLEAKS_STATUS="FAIL"
TRIVY_STATUS="FAIL"
SBOM_STATUS="FAIL"

# Validate pip-audit
if grep -q "No known vulnerabilities found" ./security-scan-results/01-pip-audit.txt 2>/dev/null; then
    PIP_AUDIT_STATUS="PASS"
fi

# Validate bandit
if grep -q "No issues identified" ./security-scan-results/02-bandit.txt 2>/dev/null; then
    BANDIT_STATUS="PASS"
fi

# Validate gitleaks
if grep -q "no leaks found" ./security-scan-results/03-gitleaks_output.txt 2>/dev/null; then
    GITLEAKS_STATUS="PASS"
fi

# Validate trivy
if [ "${TRIVY_EXIT_CODE:-1}" -eq 0 ]; then
    TRIVY_STATUS="PASS"
fi

# Validate SBOM
if [ -f "./security-scan-results/06-sbom-cyclonedx.json" ]; then
    SBOM_STATUS="PASS"
fi

cat <<EOF > $CHECKLIST_FILE
# Deployment Controls Checklist

Service: azure-devops-mcp  
Framework: FastAPI + FastMCP
Deployment Model: Docker container behind reverse proxy
Scan Date: $DATE  

---

# 1. Dependency Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Dependency vulnerability scan | Python dependencies scanned with pip-audit | $PIP_AUDIT_STATUS | 01-pip-audit.txt |
| Static code scan | Source code scanned using Bandit | $BANDIT_STATUS | 02-bandit.txt |
| Secret scanning | Repository scanned for leaked credentials | $GITLEAKS_STATUS | 03-gitleaks_output.txt |

---

# 2. Container Security

| Control | Requirement | Status | Evidence |
|---|---|---|---|
| Container vulnerability scan ($TRIVY_PACKAGE_COUNT) | Image scanned with Trivy (no critical vulnerabilities) | $TRIVY_STATUS | 05-trivy.txt |
| SBOM generation | Software Bill of Materials generated | $SBOM_STATUS | 06-sbom-cyclonedx.json |

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
| Dependency Scan | $PIP_AUDIT_STATUS |
| Static Security Scan | $BANDIT_STATUS |
| Secret Scan | $GITLEAKS_STATUS |
| Container Scan | $TRIVY_STATUS |
| SBOM | $SBOM_STATUS |

EOF

echo "Deployment checklist generated:"
echo "$CHECKLIST_FILE"
