terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    # Dùng để zip code Lambda
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }

  # State lưu trên S3 (bucket do bootstrap tạo).
  # "bucket" không hardcode, truyền vào lúc init:
  #   terraform init -backend-config="bucket=<tên-bucket>"
  backend "s3" {
    key          = "sqs-lambda-test/terraform.tfstate" # phải nằm trong prefix CI role được phép
    region       = "ap-southeast-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project    = var.name_prefix
      managed_by = "terraform"
      stack      = "sqs-lambda-test"
    }
  }
}
