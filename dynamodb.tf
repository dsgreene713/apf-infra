locals {
  dynamo_account_table = "apf-aws-accounts"
}

module "dynamodb-table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0.1"

  name                        = "apf-aws-accounts"
  hash_key                    = "acct_id"
  range_key                   = "acct_email"
  table_class                 = "STANDARD"
  deletion_protection_enabled = false

  attributes = [
    {
      name = "acct_id"
      type = "S"
    },
    {
      name = "acct_email"
      type = "S"
    },
  ]

  tags = {}
}