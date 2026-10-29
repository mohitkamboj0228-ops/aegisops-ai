# Validation — v2

Verified locally:

- 19 automated tests: policy checks, HTTP API lifecycle, AI transport mocks, provider-failure redaction, source credential exclusion, remediation approval/apply/reapply rejection/rollback/audit, and reproducible release packaging.
- TypeScript compilation and Vite production build.
- CloudFormation templates passed cfn-lint.
- Installer bash syntax and Python modules compiled successfully.
- Earlier HTTP smoke test verified built asset delivery and database persistence after a real process restart.

Not verified locally:

- Live Bedrock/Anthropic inference: credentials unavailable; provider transport tests are mocked.
- AWS deployment, SSM and IAM behavior: no authenticated AWS session.
- Docker image runtime and Kubernetes: Docker/cluster unavailable. GitHub CI will attempt the image build after publication.
- Browser layout/click-through: the browser executable download failed in this environment.

GitHub publication status is reported in the conversation and can be verified from the actual branch/PR URL. The project remains a single-user workspace with advisory AI and reviewed file-snapshot remediation; it does not autonomously modify live cloud resources.
