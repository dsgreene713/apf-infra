locals {
  lambda_handler            = "main.lambda_handler"
  lambda_runtime            = "python3.12"
  lambda_base_source_path   = "${path.module}/src/functions"
  lambda_base_output_path   = "/tmp"
  tfe_acct_import_workspace = "ws-dXx87gAzU5NRYzFH"

  # function name constants
  lambda_names = {
    apf_account_create           = "apf-account-create"
    apf_account_describe         = "apf-account-describe"
    apf_account_describe_request = "apf-account-describe-request"
    apf_service_quotas_update    = "apf-service-quotas-update"
    apf_persist_data             = "apf-persist-data"
    apf_tf_workspace_import      = "apf-tf-workspace-import"
  }

  # dynamically generate arns to prvent circular loops with dependent resources
  lambda_arns = {
    for k, v in local.lambda_names : k => "arn:aws:lambda:${local.arn_account_slug}:function:${v}"
  }

  # function configuration definition
  lambdas = {
    (local.lambda_names.apf_account_create) = {
      description     = "lambda to create org account"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_account_create}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_account_create.json]
    }
    (local.lambda_names.apf_account_describe_request) = {
      description     = "lambda to describe account creation request"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_account_describe_request}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_account_describe_request.json]
    }
    (local.lambda_names.apf_service_quotas_update) = {
      description     = "lambda to update service quotas"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_service_quotas_update}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_service_quotas_update.json]
    }
    (local.lambda_names.apf_account_describe) = {
      description     = "lambda to describe org account"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_account_describe}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_account_describe.json]
    }
    (local.lambda_names.apf_persist_data) = {
      description     = "lambda to write to dynamodb"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_persist_data}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_persist_data.json]

      environment_vars = {
        DYNAMODB_ACCT_TABLE = local.dynamo_account_table
      }
    }
    (local.lambda_names.apf_tf_workspace_import) = {
      description     = "lambda to import and apply tfe workspace config"
      handler         = local.lambda_handler
      runtime         = local.lambda_runtime
      source_path     = "${local.lambda_base_source_path}/${local.lambda_names.apf_tf_workspace_import}"
      iam_policy_docs = [data.aws_iam_policy_document.apf_tf_workspace_import.json]

      environment_vars = {
        TFE_AUTH_TOKEN_SECRET     = local.tfe_auth_token_secret
        TFE_ACCT_IMPORT_WORKSPACE = local.tfe_acct_import_workspace
        DYNAMODB_ACCT_TABLE       = local.dynamo_account_table
        ACCT_STATUS_ATTRIBUTE     = local.acct_status_attribute
        ACCT_STATUS_GSI           = local.acct_status_gsi_name
        BASE_OUTPUT_PATH          = local.lambda_base_output_path
      }
    }
  }
}

######################################################################################
# provision lambdas
######################################################################################
module "lambdas" {
  source  = "app.terraform.io/blunatech-demo/lambda-wrapper-lite/aws"
  version = "~> 1.0.5"

  for_each = local.lambdas

  function_name                    = each.key
  description                      = each.value.description
  function_handler                 = local.lambda_handler
  function_runtime                 = local.lambda_runtime
  lambda_source_dir                = "${local.lambda_base_source_path}/${each.key}"
  additional_json_policy_documents = try(each.value.iam_policy_docs, [])
  environment_variables            = try(each.value.environment_vars, {})
}

######################################################################################
# lambda iam policy docs
# each lambda gets its own policy to ensure least privilege
######################################################################################
data "aws_iam_policy_document" "apf_account_create" {
  statement {
    effect = "Allow"
    actions = [
      "organizations:TagResource",
      "organizations:CreateAccount",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "apf_account_describe_request" {
  statement {
    effect = "Allow"
    actions = [
      "organizations:DescribeCreateAccountStatus",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "apf_account_describe" {
  statement {
    effect = "Allow"
    actions = [
      "organizations:DescribeAccount",
    ]
    resources = ["arn:aws:organizations::${data.aws_caller_identity.current.account_id}:account/o-*/*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "organizations:ListAccounts",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "apf_service_quotas_update" {
  statement {
    effect = "Allow"
    actions = [
      "servicequotas:RequestServiceQuotaIncrease",
      "servicequotas:ListRequestedServiceQuotaChangeHistory",
      "servicequotas:GetServiceQuota",
      "servicequotas:ListAWSDefaultServiceQuotas",
      "servicequotas:ListServiceQuotas",
      "servicequotas:GetAWSDefaultServiceQuota",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "apf_persist_data" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
    ]
    resources = ["arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/*"]
  }
}

data "aws_iam_policy_document" "apf_tf_workspace_import" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [
      "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:${local.tfe_auth_token_secret}",
      "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:${local.tfe_auth_token_secret}*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:Query",
    ]
    resources = ["arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/*"]
  }
}