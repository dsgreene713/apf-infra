terraform {
  required_version = "~> 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.32"
    }
  }

  cloud {
    organization = "blunatech-demo"

    workspaces {
      project = "apf-infra"
      name    = "apf-infra-us-east-1"
    }
  }
}