resource "aws_dynamodb_table" "auth" {
  name         = var.auth_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    ManagedBy = "Terraform"
    Project   = "dev-workspace-mcp-project"
  }
}
