locals {
  dynamo_account_table  = "apf-aws-accounts"
  acct_id_attribute     = "acct_id"
  acct_status_attribute = "acct_status"
  acct_status_gsi_name  = "AccountStatusIndex"


  seed_data = [
    {
      acct_id           = { S = "905418152209" },
      acct_email        = { S = "dsgreene713+dummy10@gmail.com" },
      acct_name         = { S = "dummy10" },
      imported_to_state = { S = "true" },
      acct_status       = { S = "active" },
    },
    {
      acct_id           = { S = "590183719401" },
      acct_email        = { S = "dsgreene713+dummy11@gmail.com" },
      acct_name         = { S = "dummy11" },
      imported_to_state = { S = "true" },
      acct_status       = { S = "active" },
    },
    {
      acct_id           = { S = "975049936029" },
      acct_email        = { S = "dsgreene713+dummy12@gmail.com" },
      acct_name         = { S = "dummy12" },
      imported_to_state = { S = "true" },
      acct_status       = { S = "active" },
    },
  ]
}

# stores aws account metadata after pipeline provisioning
module "aws-accounts" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = "~> 4.0.1"

  name                        = local.dynamo_account_table
  hash_key                    = local.acct_id_attribute
  table_class                 = "STANDARD"
  deletion_protection_enabled = false
  billing_mode                = "PAY_PER_REQUEST"

  attributes = [
    {
      name = local.acct_id_attribute
      type = "S"
    },
    {
      name = local.acct_status_attribute
      type = "S"
    },
  ]

  global_secondary_indexes = [
    {
      name            = local.acct_status_gsi_name
      hash_key        = local.acct_status_attribute
      projection_type = "ALL"
    }
  ]

  tags = {}
}

resource "aws_dynamodb_table_item" "seed" {
  for_each = { for acct in local.seed_data : acct.acct_id["S"] => acct }

  table_name = local.dynamo_account_table
  hash_key   = local.acct_id_attribute
  item       = jsonencode(each.value)
}