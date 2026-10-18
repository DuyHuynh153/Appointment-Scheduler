variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "github_repo" {
  description = "GitHub repo (owner/name) allowed to assume the CI role. Case-sensitive."
  type        = string
  default     = "DuyHuynh153/Appointment-Scheduler"
}

variable "github_branch" {
  description = "Branch allowed to assume the CI role"
  type        = string
  default     = "master"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state"
  type        = string
  default     = "duyhuynh-tfstate-061051249721"
}

variable "name_prefix" {
  description = "Prefix of every resource the CI role is allowed to manage"
  type        = string
  default     = "sqs-lambda-test"
}

variable "github_repo_with_ids" {
  description = "Repo in GitHub's ID-qualified OIDC sub format: owner@ownerId/repo@repoId"
  type        = string
  default     = "DuyHuynh153@87678876/Appointment-Scheduler@1326922400"
}
