resource "google_compute_instance" "web" {
  # This block models the existing VM so Terraform can import and manage it.
  name         = var.vm_name
  machine_type = var.vm_machine_type
  zone         = var.zone

  can_ip_forward             = false
  deletion_protection        = false
  enable_display             = false
  key_revocation_action_type = "NONE"
  labels                     = {}
  tags                       = var.vm_tags

  boot_disk {
    auto_delete = true
    device_name = var.vm_name
    mode        = "READ_WRITE"
    source      = var.vm_boot_disk_source
  }

  network_interface {
    network    = var.vm_network
    subnetwork = var.vm_subnetwork

    access_config {
      network_tier = var.vm_network_tier
    }
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  reservation_affinity {
    type = "ANY_RESERVATION"
  }

  service_account {
    email  = var.vm_service_account_email
    scopes = var.vm_service_account_scopes
  }

  confidential_instance_config {
    enable_confidential_compute = false
  }

  shielded_instance_config {
    enable_secure_boot          = false
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  # GCP injects time-limited SSH metadata entries. We are not managing them here.
  lifecycle {
    ignore_changes = [
      metadata,
    ]
  }
}
