data "aws_organizations_organization" "this" {}
data "aws_caller_identity" "current" {}

locals {
  aws_region       = "us-east-1"
  arn_account_slug = "${local.aws_region}:${data.aws_caller_identity.current.account_id}"

  common_tags = {
    "provisioned-by"  = "apf-launchpad"
    "provisioned-for" = "apf-development"
  }
}
