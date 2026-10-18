terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Không có block backend: bootstrap dùng state local,
  # vì chính stack này tạo ra S3 bucket chứa state.
}

provider "aws" {
  region = var.aws_region

  # Tag tự động gắn vào mọi resource, để dễ tìm và dọn dẹp
  default_tags {
    tags = {
      project    = var.name_prefix
      managed_by = "terraform"
      stack      = "bootstrap"
    }
  }
}
