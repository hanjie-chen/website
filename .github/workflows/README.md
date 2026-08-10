# GitHub Actions Workflows

This directory contains the repository's continuous integration, production
deployment, content synchronization, infrastructure reconciliation, and
container security automation.

## Workflow index

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| [`ci.yml`](ci.yml) | Pushes and pull requests targeting `main`, or manual dispatch | Validates Compose and shell scripts, runs application checks, tests the container remediation helper, scans pinned third-party images, tests the candidate runtime and Daily Brief WAF exclusions, and publishes first-party images on a push. |
| [`cd.yml`](cd.yml) | Successful `CI` completion on `main` | Deploys the exact successful commit to production, validates the deployment, and cleans up old images. |
| [`container-security.yml`](container-security.yml) | Daily at 03:45 Asia/Singapore, or manually | Rescans pinned NGINX/ModSecurity and Dozzle images, tests newer remediation candidates, creates or updates a security upgrade PR when a candidate passes, manages the actionable-vulnerability issue, and verifies production image references. |
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
normal Dependabot PR -> CI scan and candidate runtime checks -> review and merge -> CD
daily container scan -> actionable HIGH/CRITICAL finding -> scan newer image tags
clean candidate -> security remediation PR -> explicitly dispatched CI -> review and merge -> CD
no clean candidate -> keep the GitHub security issue open -> retry on the next scan
```

When the daily scan finds an actionable vulnerability, it looks up newer tags
using [`../../scripts/security/container_remediation.py`](../../scripts/security/container_remediation.py)
and the image policies in
[`../../scripts/security/container-images.json`](../../scripts/security/container-images.json). It
tries candidates from newest to oldest and accepts only an immutable digest
whose Trivy scan contains no fixable HIGH/CRITICAL findings. The workflow then
creates or refreshes the bot-owned
`container-security/remediate-pinned-images` branch and opens one reviewed
security PR for the accepted image changes. Normal Dependabot updates retain
their cooldown because this path runs only after the pinned image fails the
security policy.

The scan job still fails intentionally after creating or updating the security
issue and remediation PR. Its annotation and summary distinguish the policy
failure from a runner failure and explain whether a clean candidate or PR was
available.

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
`GITHUB_TOKEN`. The daily security workflow uses a job-scoped token with
`contents`, `issues`, `pull-requests`, and `actions` write permissions to manage
one security issue, its bot-owned remediation branch and PR, and the explicit
CI dispatch for that branch. Other jobs retain read-only repository access.

Repository administrators must enable **Settings > Actions > General > Allow
GitHub Actions to create and approve pull requests**. If it is disabled, the
workflow keeps the security issue open and reports that a clean candidate was
found, but deliberately does not leave an orphan remediation branch. Pull
requests created with `GITHUB_TOKEN` do not recursively trigger workflows, so
the security job explicitly dispatches `ci.yml` against the remediation branch.

## Failure and maintenance notes

- A failing CI run blocks the corresponding CD run.
- Production runtime validation and rollback are implemented by
  [`../../scripts/deploy/prod_deploy.sh`](../../scripts/deploy/prod_deploy.sh).
- Temporary vulnerability exceptions live in
  [`../../scripts/security/trivyignore.yaml`](../../scripts/security/trivyignore.yaml)
  and must include a reason and an expiry date.
- Container image versions and immutable digests are declared in
  [`../../compose.yml`](../../compose.yml); do not edit resolved image references
  only in a workflow.
- Keep workflow-specific implementation details in the YAML and update this
  README when adding, removing, renaming, or materially changing a workflow.
