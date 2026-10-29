# AegisOps AI

A working local DevSecOps policy workspace built from the original frontend scaffold. Create projects, inspect infrastructure configuration, review remediation guidance, and maintain a persistent scan/finding history.

**Scope:** single-user policy workspace with optional real AI review (Anthropic or Amazon Bedrock), reviewed automatic configuration fixes, audit history and AWS deployment automation. AI output is advisory. Automatic remediation updates versioned workspace snapshots, not your Git repository or live infrastructure. Cloud access is private through SSM; this is not a public multi-user service.

## Downloaded runnable package

The ZIP includes a prebuilt frontend. With Python 3.12+ installed, extract all files and double-click `Start-AegisOps.bat` on Windows, or run `./start.sh` on macOS/Linux. Open http://127.0.0.1:8080. Keep the terminal running. Source checkouts require the frontend build below. For optional Bedrock support, install `backend/requirements-ai.txt` first.

## Run locally

Requirements: Node.js 24, npm, Python 3.12+.

```bash
cd frontend
npm ci
npm run build
cd ..
python3 backend/server.py
```

Open http://127.0.0.1:8080. For frontend development, run `npm run dev` from `frontend` in another terminal; Vite proxies `/api` to the backend. No Python packages are needed for scanning, remediation or the Anthropic transport. Bedrock requires `python3 -m pip install -r backend/requirements-ai.txt`.

Alternative with Docker Compose:

```bash
docker compose up --build -d
```

Open the same address. SQLite persists in the named `aegis-data` volume; `docker compose down` preserves it. `docker compose down -v` deletes stored project and finding data.

## Walkthrough

1. Open Projects and create a project, optionally adding its HTTPS GitHub URL.
2. Open Policy scans, select the project and file type.
3. Paste a Dockerfile, Kubernetes manifest, or Terraform configuration. The supplied examples intentionally contain issues.
4. Run checks; review the severity, rule ID, and suggested fix.
5. Edit the text and rescan. Previous runs remain in history.
6. Acknowledge or resolve findings in Incidents. Status changes record a review, not an infrastructure change.
7. Restart the backend to verify project and scan history persists.

The overview uses stored API data. No sample performance metrics are presented as real outcomes. A fresh workspace starts empty.

## Supported checks

- Dockerfile: explicit non-root user, `latest` base image, health check.
- Kubernetes workload YAML: privileged mode, host networking, non-root policy, resource limits and readiness probe.
- Terraform text: internet-wide CIDR indicators, encryption explicitly disabled, public storage ACLs.
- Potential AWS access-key IDs and private-key headers.

**Limitations:** regex checks are not semantic parsers. They may flag comments, miss nested/multistage configurations or miss other vulnerabilities. The score is a local heuristic; passing does not establish compliance. An internet-wide CIDR may be legitimate egress and requires review. Use Trivy, Checkov, a secret scanner and human review in real delivery workflows. Scans are synchronous, text-only, capped at 20 files and 256 KiB per request. Source snapshots are persisted in local SQLite to support remediation. Files detected by the credential rule are excluded from snapshot storage; this detector cannot identify all secret types. Do not submit actual secrets. Findings contain file names, rule names and remediation text.

## Test and build

```bash
python3 -m unittest discover -s backend/tests -v
cd frontend
npm run build
```

CI runs these checks and builds the container on GitHub Actions after the changes are pushed. The separate manually invoked `Deploy AWS workspace` workflow provisions and verifies an AWS instance using OIDC after the bootstrap and repository variables are configured. See [AWS setup](deploy/AWS_SETUP.md).

## API

- `GET /api/health`: process health.
- `GET /api/state`: projects, latest 100 scans, latest 500 findings.
- `POST /api/projects`: `{ "name": "demo", "url": "https://github.com/owner/repo" }`.
- `POST /api/scans`: `{ "project_id": "returned-id", "files": { "Dockerfile": "FROM ..." } }`.
- `POST /api/ai/analyze`: `{ "scan_id": "id" }` invokes the configured AI provider.
- `POST /api/remediation/preview`: `{ "scan_id": "id" }` creates a pending diff.
- `POST /api/remediation/apply`: `{ "plan_id": "id", "approved": true }` applies allowlisted fixes to a new snapshot and rescans.
- `POST /api/remediation/rollback`: same payload; restores original content as another snapshot.
- `POST /api/incidents/status`: `{ "id": "returned-id", "status": "acknowledged" }` (also `open`, `resolved`).

SQLite location defaults to `data/aegis.db`; change with `AEGIS_DB`. `AEGIS_HOST` defaults to loopback, `PORT` to 8080. Do not expose the unauthenticated API publicly. The container binds internally to all interfaces but Compose publishes only loopback. Browser mutation requests enforce JSON and reject unexpected origins/hosts.

## AI configuration

Set environment variables in the server process (local startup does not automatically load `.env`). For Docker Compose, `.env` supplies its configured environment variables.

| Provider | Configuration |
| --- | --- |
| Anthropic | `AEGIS_AI_PROVIDER=anthropic`, `AEGIS_AI_MODEL=<available model ID>`, `ANTHROPIC_API_KEY=<server-side key>` |
| Amazon Bedrock | `AEGIS_AI_PROVIDER=bedrock`, `AEGIS_AI_MODEL=<authorized model ID/ARN>`, `AWS_REGION=<region>` and standard AWS SDK credentials/instance role |
| Disabled | `AEGIS_AI_PROVIDER=disabled` (default) |

Bedrock uses boto3 Converse. Anthropic uses its HTTPS Messages API. No hardcoded model ID is assumed because access and availability vary. Configuration indicates settings are present, not a successful connectivity check. Provider failures are reported without exposing keys. Raw file contents and file paths are not sent to the model; only fixed rule metadata is transmitted. Usage may incur provider charges.

## Reviewed automatic remediation

After scanning a file, choose **Preview automatic fixes**, inspect the diff, approve updating the workspace snapshot, then apply and rescan. Export the resulting JSON snapshot to review/use the edited files. Remediation history can restore the original configuration as a new snapshot. Audit events are persisted. Reapplying a consumed plan is rejected.

The allowlist replaces explicit YAML `privileged: true`/`hostNetwork: true` with `false`, and Terraform `encrypted = false`/public storage ACL declarations with hardened values. It does not invent Docker user IDs, image versions, network CIDRs, resource limits or health endpoints. These edits are text-based and require testing; they can affect workload behavior. AI suggestions cannot invoke commands or trigger cloud changes. Historical findings remain attached to their original scans.

Existing scans created before v2 have no source snapshot and must be rescanned before remediation. Snapshots and analysis records are local data; protect and back up the database.

## AWS and Kubernetes deployment

See [AWS_SETUP.md](deploy/AWS_SETUP.md) for the supplied account bootstrap, GitHub OIDC role, deployment workflow, private SSM access and costs/data limitations. This setup needs AWS/account access and a connected GitHub write capability to publish/run it. It has not been deployed from the authoring environment.

`deploy/kubernetes.yaml` remains an optional container path: replace its image placeholder, use a cluster with a default storage class, keep replicas at one, and access via `kubectl port-forward deployment/aegisops 8080:8080`. AI provider environment/credentials must be configured separately. The Kubernetes manifest has not been applied here.

Before public production use, add identity/authentication, authorization, TLS, rate limiting, background workers, a production database and off-instance backups. Autonomous live-cloud remediation requires a separately reviewed permission and rollback model.
