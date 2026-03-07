data "http" "cloudflare_ipv4" {
  # Pull the current Cloudflare IPv4 list from the official endpoint.
  url = var.cloudflare_ipv4_source_url
}

locals {
  # Convert the plaintext response body into a clean CIDR list.
  cloudflare_ipv4_cidrs = [
    for cidr in split("\n", trimspace(data.http.cloudflare_ipv4.response_body)) : trimspace(cidr)
    if trimspace(cidr) != ""
  ]
}

check "cloudflare_ipv4_not_empty" {
  assert {
    # Fail fast if the upstream list could not be fetched or parsed.
    condition     = length(local.cloudflare_ipv4_cidrs) > 0
    error_message = "Failed to load Cloudflare IPv4 ranges from the configured source URL."
  }
}

resource "google_compute_firewall" "allow_cf_https" {
  # Model the existing rule that only allows Cloudflare to reach the origin on HTTPS.
  name        = var.firewall_allow_cf_https_rule_name
  description = var.firewall_allow_cf_https_description
  network     = var.vm_network

  direction     = "INGRESS"
  priority      = 100
  source_ranges = local.cloudflare_ipv4_cidrs

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}
