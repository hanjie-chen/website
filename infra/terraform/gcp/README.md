# GCP Terraform

Terraform configuration for the website's existing GCP environment. Application
deployment is handled separately by the [deploy scripts](../../../scripts/deploy/README.md);
VM bootstrap is in [infra/ansible](../../ansible/).

## Managed Resources

| Configuration | Scope |
| --- | --- |
| [compute.tf](compute.tf) | `google_compute_instance.web`: existing VM, boot disk attachment, network and service account settings; metadata changes are ignored |
| [firewall.tf](firewall.tf) | `google_compute_firewall.allow_cf_https`: allow TCP 443 from dynamically fetched Cloudflare IPv4 ranges |
| [monitoring.tf](monitoring.tf) | `google_monitoring_uptime_check_config.website_https` and optional `google_monitoring_notification_channel.email[0]` |

`notification_email_address` defaults to empty, so the email channel is not
managed unless an address is supplied. Alert policies are not defined here;
creating a channel alone does not configure an alert policy.

Default VPC firewall rules and Cloudflare account settings (Access, cache, TLS
mode and rate limiting) are outside this configuration. The managed firewall
rule adds an allow rule; it does not establish that other rules deny direct
origin access. Only Cloudflare IPv4 ranges are fetched by this module.

## State and Configuration

[foundation.tf](foundation.tf) declares Terraform `>= 1.6.0`, Google/HTTP provider
constraints and a GCS backend at `gs://my-web-tfstate/terraform/state`. Access to
the state bucket is required in addition to permissions for managed resources.
Commit [.terraform.lock.hcl](.terraform.lock.hcl) when provider selections change.

[variables.tf](variables.tf) contains the production project, location, existing
VM/disk/network references and monitoring settings. Review these defaults before
using another environment. Changing variables does not select a separate state
backend automatically.

Local `terraform.tfvars` is Git-ignored. Any overrides used locally must also be
supplied to automation when appropriate; the current workflow does not inject
`notification_email_address`. Review a plan before changing it back to empty,
since this removes the configured email-channel instance from the resource set.

`uptime_check_path` defaults to `/`, checking the public homepage through its
language redirect. The check accepts a final 2xx response and validates TLS.
It checks website entry availability, not article database health; article routes
are covered separately by deployment smoke checks.

## Local Workflow

Authenticate using local Application Default Credentials and run from this directory:

```bash
gcloud auth application-default login
cd infra/terraform/gcp  # from the repository root
terraform init
terraform validate
terraform plan -out=tfplan
```

Inspect the saved plan, including replacements and deletions, then apply that
reviewed plan when intended:

```bash
terraform apply tfplan
```

Planning refreshes data sources, including the configured Cloudflare IPv4 URL.
The VM resource has deletion protection disabled; its existing-resource modeling
is not a guarantee against replacement when configuration changes.

## Importing Existing Resources

The initial setup adopted existing resources. Imports are a recovery or adoption
step, not part of routine deployment. Check the selected backend and current
state first, then import only a resource not already tracked. For example:

```bash
terraform state list
terraform import google_compute_instance.web \
  'projects/<project_id>/zones/<zone>/instances/<vm_name>'
terraform plan
```

The other resource addresses are listed above. Use the actual resource IDs from
the target project rather than copied historical IDs. Review configuration drift
after import before applying any proposed changes.

## Automation

[infra-sync.yml](../../../.github/workflows/infra-sync.yml) uses GCP Workload
Identity Federation with the `GCP_WIF_PROVIDER` and
`GCP_TERRAFORM_SERVICE_ACCOUNT` Actions secrets. Both scheduled and manual runs
validate, plan and automatically apply a saved plan when changes are detected.
This can reconcile any managed resource, not only Cloudflare firewall CIDRs.
Triggers, permissions and concurrency are documented in the
[workflow guide](../../../.github/workflows/README.md).
