# AWS + GitHub deployment setup

No passwords, access-key pairs, GitHub tokens or OTPs need to be shared in chat. The deployment uses GitHub OIDC temporary credentials; the application uses its EC2 instance role for Bedrock.

## 1. Bootstrap your AWS account

An AWS administrator performs this once in the chosen region:

1. Open CloudFormation and create a stack from `deploy/bootstrap-oidc.yaml`.
2. Keep Repository as `mohitkamboj0228-ops/aegisops-ai`.
3. For CreateOidcProvider, use `true` only if IAM does not already have the `token.actions.githubusercontent.com` identity provider; otherwise leave `false`.
4. Optionally supply a regional Bedrock model ARN with Converse support. Model availability/access depends on the region and your account. Keep it blank to deploy with AI disabled, then update the bootstrap/app settings later.
5. Acknowledge IAM resource creation, review the template and create the stack.
6. Record its outputs: DeploymentRoleArn, ArtifactBucketName and RuntimeProfileName. These identifiers are not passwords.

The template creates a private encrypted/versioned S3 bucket, an EC2 runtime role, its instance profile and a repository/environment-scoped deployment role. The deployment role can provision EC2/security-group resources in the selected region and operate the `aegisops-app` stack; it can pass only the created runtime role. Review this provisioning authority before granting access. The bootstrap role needs no GitHub access token.

## 2. Configure the repository

After the code has been pushed:

1. Create the GitHub repository environment `aws-production`.
2. Restrict its deployment branches to the intended trusted branch (normally `main`). Use a required reviewer if appropriate for your workflow.
3. Set these environment variables (not source-code constants):

| Variable | Value |
| --- | --- |
| `AWS_DEPLOY_ROLE_ARN` | Bootstrap DeploymentRoleArn output |
| `AWS_REGION` | Selected AWS region |
| `AWS_ARTIFACT_BUCKET` | Bootstrap ArtifactBucketName output |
| `AWS_INSTANCE_PROFILE` | Bootstrap RuntimeProfileName output |
| `AWS_VPC_ID` | Existing VPC ID |
| `AWS_SUBNET_ID` | Existing public subnet ID in that VPC |
| `BEDROCK_MODEL_ARN` | Same authorized model ARN, or blank to disable AI |

The subnet needs an internet-gateway route and DNS/outbound connectivity so installation, S3, SSM and Bedrock can work. The new security group has **no inbound rules**. The instance receives a public address for outbound access, but the application listens only on localhost. Access is through Session Manager forwarding; this is a personal workspace, not a public SaaS deployment.

The OIDC trust subject is exactly `repo:mohitkamboj0228-ops/aegisops-ai:environment:aws-production`. Repository administrators must protect that environment; the AWS trust policy alone does not select a branch.

## 3. Run deployment

In GitHub Actions, run **Deploy AWS workspace** from the trusted branch. The workflow tests the API, builds the frontend, requests temporary AWS credentials, uploads a content-addressed release, creates/updates CloudFormation, installs through SSM, and checks the running health endpoint. The action prints an SSM forwarding command only after health verification succeeds.

CloudFormation success alone is not an application health check. A workflow failure requires inspection of its logs, SSM command status, `/var/log/aegis-bootstrap.log` or `journalctl -u aegisops` on the instance.

For an authenticated local AWS CLI/SSO environment, the same deployment can run with Python:

```bash
python3 -m pip install -r backend/requirements-ai.txt
npm ci --prefix frontend
npm run build --prefix frontend
python3 deploy/aws_deploy.py --region YOUR_REGION --bucket YOUR_ARTIFACT_BUCKET --vpc YOUR_VPC_ID --subnet YOUR_SUBNET_ID --profile YOUR_INSTANCE_PROFILE --model YOUR_BEDROCK_MODEL_ARN
```

Do not paste AWS keys into these commands or chat. Use your normal AWS SSO/temporary-credential login. Model and resource IDs are supplied as command arguments; shell-quote your values where necessary.

## 4. Open the workspace

Run the printed `aws ssm start-session` command on a machine with AWS CLI and the Session Manager plugin, then open `http://127.0.0.1:8080`. The operator needs Session Manager permissions for that instance. The GitHub deploy role intentionally has no interactive-session access.

## Updates, costs and data

- Resources include one `t3.small`, 20 GiB encrypted gp3 storage, an IPv4 address and S3 storage; Bedrock inference is billed separately. Check regional pricing before creating the stack.
- SQLite data is stored at `/var/lib/aegis`. Each code deployment creates a local predeployment database backup and keeps prior app releases. On failed application health verification, the installer attempts to restore the prior code release. This does not roll back database migrations or environment settings; review them separately.
- Backups on the same root disk do not protect against disk/instance deletion. Export data or create EBS snapshots before destructive changes. Root disk data is deleted when the instance terminates. This setup has no high availability or off-instance backup schedule.
- The deploy script preserves the existing AMI and rejects VPC/subnet changes during ordinary updates to avoid unexpected instance replacement. OS patching/image upgrades require a separate reviewed maintenance process.
- Deleting the application stack removes its instance and disk. The bootstrap artifact bucket is retained; old releases and S3 versions continue to incur storage charges until intentionally removed.
- Neither CloudFormation nor a live Bedrock call was executed in the authoring environment. The templates passed local `cfn-lint`; real model access, IAM/SCP rules, network access and provisioning must be verified in your account.

## Official references

- [GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [AWS Bedrock Converse API](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html)
- [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create)
