locals {
  step_function_names = {
    apf_root = "apf-root-workflow"
  }

  step_functions = {
    (local.step_function_names.apf_root) = {
      lambda_arns = values(local.lambda_arns)
      definition  = jsonencode(yamldecode(templatefile("${path.module}/workflows/apf-workflow.yaml", local.lambda_arns)))
    }
  }
}

module "stepfunctions-wrapper" {
  source  = "app.terraform.io/blunatech-demo/stepfunctions-wrapper/aws"
  version = "~> 1.0.0"

  state_machines = local.step_functions
}