output "auth_table_name" {
  value       = aws_dynamodb_table.auth.name
  description = "Set this value as AUTH_TABLE_NAME for the Lambda."
}

output "auth_table_arn" {
  value       = aws_dynamodb_table.auth.arn
  description = "DynamoDB table ARN"
}
