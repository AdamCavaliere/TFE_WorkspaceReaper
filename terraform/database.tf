resource "aws_dynamodb_table" "base-dynamodb-table" {
  name           = "WorkspaceReaper-${var.TFE_ORG}"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "workspaceId"

  attribute {
    name = "workspaceId"
    type = "S"
  }
}
