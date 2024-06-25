locals {
  compatible_runtimes    = ["python3.12"]
  layer_base_source_path = "${path.module}/src/layers"

  layer_names = {
    tfe_client = "tfe-client"
  }

  layer_arns = {
    for k, v in local.layer_names : k => "arn:aws:lambda:${local.arn_account_slug}:function:${v}"
  }

  layers = {
    (local.layer_names.tfe_client) = {
      description         = "layer to interacte with tfe api"
      source_path         = "${local.layer_base_source_path}/${local.layer_names.tfe_client}"
      artifacts_dir       = "${path.module}/.terraform/layer-builds"
      compatible_runtimes = local.compatible_runtimes
    }
  }
}
