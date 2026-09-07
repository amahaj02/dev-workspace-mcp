terraform {
  backend "s3" {
    bucket       = "terraform-state-344138923336-ca-central-1-an"
    key          = "dev-workspace-mcp/terraform.tfstate"
    region       = "ca-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
