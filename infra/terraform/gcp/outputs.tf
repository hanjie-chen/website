output "vm_name" {
  description = "Name of the imported GCP VM."
  value       = google_compute_instance.web.name
}

output "vm_zone" {
  description = "Zone of the imported GCP VM."
  value       = google_compute_instance.web.zone
}

output "vm_internal_ip" {
  description = "Internal IPv4 address of the VM."
  value       = google_compute_instance.web.network_interface[0].network_ip
}

output "vm_external_ip" {
  description = "External IPv4 address of the VM."
  value       = google_compute_instance.web.network_interface[0].access_config[0].nat_ip
}
