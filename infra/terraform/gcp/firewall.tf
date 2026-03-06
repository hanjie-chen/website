resource "google_compute_firewall" "allow_cf_https" {
  # Model the existing rule that only allows Cloudflare to reach the origin on HTTPS.
  name        = var.firewall_allow_cf_https_rule_name
  description = var.firewall_allow_cf_https_description
  network     = var.vm_network

  direction     = "INGRESS"
  priority      = 100
  source_ranges = var.cloudflare_ipv4_cidrs

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}