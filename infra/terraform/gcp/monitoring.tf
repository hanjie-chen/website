resource "google_monitoring_uptime_check_config" "website_https" {
  # Model the production HTTPS uptime check for the public site.
  display_name       = var.uptime_check_display_name
  period             = var.uptime_check_period
  timeout            = var.uptime_check_timeout
  checker_type       = "STATIC_IP_CHECKERS"
  log_check_failures = var.uptime_check_log_failures

  monitored_resource {
    type = "uptime_url"

    labels = {
      host       = var.uptime_check_host
      project_id = var.project_id
    }
  }

  http_check {
    accepted_response_status_codes {
      status_class = "STATUS_CLASS_2XX"
    }

    request_method = "GET"
    path           = var.uptime_check_path
    port           = 443
    use_ssl        = true
    validate_ssl   = true
  }
}

resource "google_monitoring_notification_channel" "email" {
  # Keep the email channel optional because the actual address is private.
  count = var.notification_email_address == "" ? 0 : 1

  display_name = var.notification_channel_display_name
  type         = "email"
  enabled      = true

  labels = {
    email_address = var.notification_email_address
  }
}
