terraform {
  # Minimum Terraform CLI version required by this configuration.
  # Your current version is v1.14.6, so it satisfies this constraint.
  required_version = ">= 1.6.0"

  required_providers {
    # Use the official Google provider and pin to major version 6.
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Remote state backend (GCS). Bucket/prefix are passed at init time:
  # terraform init -backend-config=backend.hcl
  backend "gcs" {
    bucket = "my-web-tfstate"
    prefix = "terraform/state"
  }
}

# Default Google provider used by all resources in this directory.
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
