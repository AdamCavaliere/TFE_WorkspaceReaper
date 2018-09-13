resource "aws_sqs_queue" "reaper_queue" {
  name                      = "WorkspaceReaper-${var.TFE_ORG}"
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10

  tags {
    Environment = "workspace_reaper"
  }
}
