locals {
  tfe_auth_token_secret = "tfe-auth-token-latest"
}

# tfe auth token used by lambdas to interacte with tfe api
resource "aws_secretsmanager_secret" "tfe_auth_token" {
  name = local.tfe_auth_token_secret
}

resource "aws_secretsmanager_secret_version" "tfe_auth_token" {
  secret_id     = aws_secretsmanager_secret.tfe_auth_token.id
  secret_string = var.tfe_auth_token
}