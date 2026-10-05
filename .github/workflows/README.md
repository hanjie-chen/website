# GitHub Actions Workflows

Automation for application delivery, article synchronization, GCP infrastructure
and container security. This guide covers triggers, operational boundaries and
repository setup; exact commands and action versions live in the linked YAML.

## Workflow Index

Scheduled times below use UTC. All scheduled workflows also accept manual dispatch.

| Workflow | Trigger | Responsibility |
| --- | --- | --- |
| [ci.yml](ci.yml) | Push to `main`, pull request targeting `main`, or manual dispatch | Validate code/configuration and candidate runtime; publish application images on successful `main` push checks |
| [cd.yml](cd.yml) | Successful push-triggered `CI` completion on `main` | Deploy application images tagged with the CI commit SHA, validate production and clean up old images |
| [content-sync.yml](content-sync.yml) | Manual or external `workflow_dispatch` | Sync article sources on production, then run health and smoke checks |
| [container-security.yml](container-security.yml) | Daily at 19:45 UTC (03:45 UTC+8 next day) | Scan pinned third-party images, propose security updates and check production image references |
| [infra-sync.yml](infra-sync.yml) | Sundays at 03:00 UTC (11:00 UTC+8) | Validate and plan GCP Terraform; automatically apply a plan containing changes |

## Application Delivery

```text
pull request / manual CI -> checks only
push to main -> checks -> GHCR image publication -> CD -> production validation
```

CI runs application/runtime checks and the container security gate independently.
The runtime job covers Compose, ShellCheck, Ruff, application, deployment image
cleanup and security-helper tests, coverage, Nginx configuration, service health
and smoke checks. Python `pip-audit` is advisory and does not block publication.
Runtime health checks include the daily brief cleanup service, which shares the
candidate web-app image and enforces retention independently of uploads.

The container gate normally scans changed pinned third-party image references.
Policy changes or lack of a usable comparison revision cause a full tracked-image
scan. Existing findings in unchanged images remain with the daily security
workflow. Selection rules and vulnerability exceptions are documented in
[scripts/security/README.md](../../scripts/security/README.md).

`compose-check-and-build` aggregates the results and preserves the required-check
name. On `main` pushes it also requires successful publication of `web-app` and
`articles-sync` images, tagged with both the commit SHA and `latest`. Pull requests
and manual CI runs neither publish images nor trigger CD.

CD selects application images using `workflow_run.head_sha`. The host checkout,
Compose configuration and deployment scripts are first updated to the latest
`main`; they are **not pinned to that CI SHA**. Third-party images use the
references in the host's Compose file. Deployment checks and rollback scope are
owned by [scripts/deploy/README.md](../../scripts/deploy/README.md).

## Content and Infrastructure Updates

- **Content Sync** updates the website checkout on the production host to `main`
  and invokes `articles-sync`, which always requests a reindex; a reindex failure
  fails the run. Dispatch inputs such as `source_sha` are log
  context, not a requested checkout revision. The sync service follows its
  configured source branch; see [articles-sync](../../articles-sync/README.md).
- **Terraform Infra Sync** authenticates through GCP Workload Identity Federation
  and operates in `infra/terraform/gcp`. A plan error fails the run, no changes
  skips apply, and detected changes are applied automatically from the saved
  plan. Manual dispatch follows the same behavior; it is not a plan-only mode.
  Resource and backend details are in the [GCP guide](../../infra/terraform/gcp/README.md).

## Container Security

The daily workflow scans pinned Nginx/ModSecurity and Dozzle images for actionable
HIGH/CRITICAL vulnerabilities with available fixes, using the shared exception
policy. It scans newer candidates and proposes accepted replacements through
`container-security/remediate-pinned-images`; it does not merge or deploy them.
Normal version updates are proposed separately by [Dependabot](../dependabot.yml).

When the remediation branch changes or its PR is created, the workflow explicitly
dispatches CI for that branch. Candidate runtime validation happens in CI, after
candidate vulnerability scanning. Review and merge are still required.

Actionable findings intentionally fail the scan job even if a remediation PR was
created. Read the job summary to distinguish findings from discovery, permission
or runner errors. The security issue is updated while findings remain and closed
by a subsequent clean scan. Reports are uploaded as `container-vulnerability-reports`.
Scan policy, report contents and helper usage belong in the
[security guide](../../scripts/security/README.md).

A separate job compares running third-party image references with the production
host's current `compose.yml`. It neither updates that checkout nor depends on the
scan job succeeding.

## Coordination and Repository Setup

CD, Content Sync and the production image-reference check share the
`production-deploy` concurrency group. Terraform uses `terraform-infra-sync`;
the security workflow uses `container-security`. All set `cancel-in-progress:
false` to avoid interrupting active runs. These groups do not provide a lock for
manual commands run directly on the host.

| Actions secrets | Used by |
| --- | --- |
| `SSH_HOST`, `SSH_USER`, `SSH_PORT`, `SSH_PRIVATE_KEY` | CD, Content Sync and production image-reference checks |
| `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT` | Terraform authentication |

SSH jobs expect the website checkout at `/home/plain/projects/website` on the
production host, with Docker Compose and the deployment environment prepared.

CI uses `GITHUB_TOKEN` with `packages: write` for GHCR publication. The security
scan job grants `contents`, `issues`, `pull-requests` and `actions` write access
for remediation and reporting. Terraform grants `id-token: write` for WIF.

Enable **Settings > Actions > General > Allow GitHub Actions to create and approve
pull requests** for automated remediation PRs. The workflow pushes its branch
before creating the PR; a PR permission failure can therefore leave a branch
without a PR. Inspect the remediation step logs when creation or dispatch fails.

Update this guide when triggers, publication rules, permissions or production
coordination change. Keep script internals and report formatting in their
subsystem guides.
