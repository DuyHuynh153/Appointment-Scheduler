output "github_actions_role_arn" {
  description = "Set as GitHub variable AWS_ROLE_ARN"
  value       = aws_iam_role.github_actions.arn
}

output "state_bucket_name" {
  description = "Set as GitHub variable TF_STATE_BUCKET"
  value       = aws_s3_bucket.tfstate.bucket
}

output "aws_region" {
  description = "Set as GitHub variable AWS_REGION"
  value       = var.aws_region
}
