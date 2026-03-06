# GCP Terraform

This directory contains the GCP Terraform configuration for the production website environment.

## Scope

Current Terraform coverage:

- `google_compute_instance.web`
- `google_compute_firewall.allow_cf_https`
- `google_monitoring_uptime_check_config.website_https`

Current non-managed items:

- notification channel
- alert policy
- default VPC firewall rules

## Backend

Remote state is stored in GCS via the backend declared in `foundation.tf`.

## Authentication

Current workflow uses local `gcloud` authentication / ADC.

Example:

```bash
gcloud auth application-default login
```

## Workflow

Initialize:

```bash
cd infra/terraform/gcp
terraform init
```

Check current state:

```bash
terraform plan
```

## Import-first

This configuration was aligned to existing production resources first, then imported into Terraform state.

Example import commands:

```bash
terraform import google_compute_instance.web \
  projects/base-general-487513/zones/us-west1-a/instances/free-gcp-machine

terraform import google_compute_firewall.allow_cf_https \
  projects/base-general-487513/global/firewalls/allow-cf-https

terraform import google_monitoring_uptime_check_config.website_https \
  projects/base-general-487513/uptimeCheckConfigs/website-health-check-gIPOqtZq_Fs
```

After each import, verify with:

```bash
terraform plan
```

Target state is:

```text
No changes. Your infrastructure matches the configuration.
```

## Notes

- `compute.tf` models the existing VM conservatively to avoid replacement.
- `firewall.tf` currently tracks the existing Cloudflare HTTPS allow rule only.
- `monitoring.tf` currently tracks the existing HTTPS uptime check only.
- `.terraform.lock.hcl` should be committed.
