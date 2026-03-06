#############################
# Provider / location
#############################

variable "project_id" {
  description = "GCP project ID where resources will be created."
  type        = string
  default     = "base-general-487513"
}

variable "region" {
  description = "GCP region for regional resources."
  type        = string
  default     = "us-west1"
}

variable "zone" {
  description = "GCP zone for zonal resources (for example VM)."
  type        = string
  default     = "us-west1-a"
}

#############################
# Existing VM
#############################

variable "vm_name" {
  description = "Existing VM instance name."
  type        = string
  default     = "free-gcp-machine"
}

variable "vm_machine_type" {
  description = "Machine type for the existing VM."
  type        = string
  default     = "e2-micro"
}

variable "vm_network" {
  description = "VPC network self link used by the VM NIC."
  type        = string
  default     = "https://www.googleapis.com/compute/v1/projects/base-general-487513/global/networks/default"
}

variable "vm_subnetwork" {
  description = "Subnetwork self link used by the VM NIC."
  type        = string
  default     = "https://www.googleapis.com/compute/v1/projects/base-general-487513/regions/us-west1/subnetworks/default"
}

variable "vm_network_tier" {
  description = "Network tier for the external access config."
  type        = string
  default     = "STANDARD"
}

variable "vm_boot_disk_source" {
  description = "Self link of the existing boot disk attached to the VM."
  type        = string
  default     = "https://www.googleapis.com/compute/v1/projects/base-general-487513/zones/us-west1-a/disks/free-gcp-machine"
}

variable "vm_service_account_email" {
  description = "Service account attached to the VM."
  type        = string
  default     = "1090136205625-compute@developer.gserviceaccount.com"
}

variable "vm_service_account_scopes" {
  description = "OAuth scopes attached to the VM service account."
  type        = list(string)
  default = [
    "https://www.googleapis.com/auth/devstorage.read_only",
    "https://www.googleapis.com/auth/logging.write",
    "https://www.googleapis.com/auth/monitoring.write",
    "https://www.googleapis.com/auth/service.management.readonly",
    "https://www.googleapis.com/auth/servicecontrol",
    "https://www.googleapis.com/auth/trace.append",
  ]
}

variable "vm_tags" {
  description = "Network tags currently attached to the VM."
  type        = list(string)
  default = [
    "http-server",
    "https-server",
  ]
}

#############################
# Existing firewall
#############################

variable "cloudflare_ipv4_cidrs" {
  description = "Cloudflare IPv4 ranges allowed to reach the origin directly."
  type        = list(string)
  default = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
  ]
}

variable "firewall_allow_cf_https_rule_name" {
  description = "Existing firewall rule name that allows Cloudflare to reach the origin over HTTPS."
  type        = string
  default     = "allow-cf-https"
}

variable "firewall_allow_cf_https_description" {
  description = "Existing description on the Cloudflare HTTPS firewall rule."
  type        = string
  default     = "allow https traffic from cloudflare"
}

#############################
# Monitoring
#############################

variable "uptime_check_display_name" {
  description = "Display name of the HTTPS uptime check."
  type        = string
  default     = "website-health-check"
}

variable "uptime_check_host" {
  description = "Public host monitored by the uptime check."
  type        = string
  default     = "hanjie-chen.com"
}

variable "uptime_check_path" {
  description = "HTTP path monitored by the uptime check."
  type        = string
  default     = "/articles"
}

variable "uptime_check_period" {
  description = "How often the uptime check runs."
  type        = string
  default     = "300s"
}

variable "uptime_check_timeout" {
  description = "How long the uptime check waits before timing out."
  type        = string
  default     = "10s"
}

variable "uptime_check_log_failures" {
  description = "Whether failed uptime checks are logged to Cloud Logging."
  type        = bool
  default     = true
}

variable "notification_channel_display_name" {
  description = "Display name of the email notification channel."
  type        = string
  default     = "website-email-alerts"
}

variable "notification_email_address" {
  description = "Email address for Monitoring notifications. Leave empty to skip managing the channel for now."
  type        = string
  default     = ""
}
