# GitHub Actions Workflows

This directory contains the repository's continuous integration, production
deployment, content synchronization, infrastructure reconciliation, and
container security automation.

## Workflow index

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| [`ci.yml`](ci.yml) | Pushes and pull requests targeting `main` | Validates Compose and shell scripts, runs application checks, scans pinned third-party images, tests the candidate runtime, and publishes first-party images on a push. |
| [`cd.yml`](cd.yml) | Successful `CI` completion on `main` | Deploys the exact successful commit to production, validates the deployment, and cleans up old images. |
| [`container-security.yml`](container-security.yml) | Daily at 03:45 Asia/Singapore, or manually | Rescans pinned NGINX/ModSecurity and Dozzle images, manages the actionable-vulnerability issue, and verifies production image references. |
| [`content-sync.yml`](content-sync.yml) | Manual or external `workflow_dispatch` | Pulls the current `main` branch on production, synchronizes article content, and runs health and smoke checks. |
| [`infra-sync.yml`](infra-sync.yml) | Sundays at 11:00 Asia/Singapore, or manually | Validates, plans, and applies the Terraform configuration for GCP. |

## Main execution flows

Application delivery follows this sequence:

```text
pull request -> CI checks
merge/push to main -> CI checks and image publication -> CD -> production validation
```

Third-party image maintenance follows this sequence:

```text
Dependabot PR -> CI scan and candidate runtime checks -> review and merge -> CD
daily container scan -> GitHub issue on actionable HIGH/CRITICAL findings
```

Production deployment, content synchronization, and the production-reference
check share the `production-deploy` concurrency group. They wait for each other
instead of mutating or inspecting production concurrently. Terraform uses the
separate `terraform-infra-sync` group.

## Repository configuration

Production SSH workflows require these Actions secrets:

- `SSH_HOST`
- `SSH_USER`
- `SSH_PORT`
- `SSH_PRIVATE_KEY`

Terraform additionally requires:

- `GCP_WIF_PROVIDER`
- `GCP_TERRAFORM_SERVICE_ACCOUNT`

First-party container publication uses the automatically provided
`GITHUB_TOKEN`. The daily security workflow uses the same token to manage a
single open security issue.

## Failure and maintenance notes

- A failing CI run blocks the corresponding CD run.
- Production runtime validation and rollback are implemented by
  [`../../scripts/deploy/prod_deploy.sh`](../../scripts/deploy/prod_deploy.sh).
- Temporary vulnerability exceptions live in
  [`../../.trivyignore.yaml`](../../.trivyignore.yaml) and must include a reason
  and an expiry date.
- Container image versions and immutable digests are declared in
  [`../../compose.yml`](../../compose.yml); do not edit resolved image references
  only in a workflow.
- Keep workflow-specific implementation details in the YAML and update this
  README when adding, removing, renaming, or materially changing a workflow.
