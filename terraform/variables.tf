variable "aws_region" {
  type        = string
  description = "AWS region for the application infra"
}

variable "auth_table_name" {
  type        = string
  description = "Name of the OAuth store/table"
}
