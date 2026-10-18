# ---------------------------------------------------------------
# Dữ liệu chung
# ---------------------------------------------------------------

# Lấy account ID của credential đang dùng (không cần hardcode)
data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = var.aws_region
  prefix     = var.name_prefix
}

# ---------------------------------------------------------------
# S3 bucket chứa Terraform state của các stack khác
# ---------------------------------------------------------------

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name

  # Bucket test: cho phép destroy cả khi còn object/version bên trong
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # SSE-S3, miễn phí (KMS tốn $1/tháng/key)
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------
# GitHub OIDC provider: cho phép AWS tin token do GitHub Actions cấp
# ---------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# ---------------------------------------------------------------
# IAM role mà GitHub Actions sẽ assume
# ---------------------------------------------------------------

# Trust policy: AI được assume role này
data "aws_iam_policy_document" "github_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Chỉ đúng repo này, đúng nhánh master
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  # Cố ý KHÔNG bắt đầu bằng "${local.prefix}-", để role không tự sửa được chính nó
  name                 = "gha-${local.prefix}"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

# Permission policy: role được LÀM GÌ.
# Chỉ trên resource có tên bắt đầu bằng "sqs-lambda-test-"
data "aws_iam_policy_document" "github_permissions" {
  # --- Terraform state trong S3 ---
  statement {
    sid       = "TfStateList"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.tfstate.arn]
  }

  statement {
    sid       = "TfStateObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.tfstate.arn}/${local.prefix}/*"]
  }

  # --- SQS ---
  statement {
    sid       = "Sqs"
    actions   = ["sqs:*"]
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.prefix}-*"]
  }

  # --- Lambda function ---
  statement {
    sid       = "LambdaFunction"
    actions   = ["lambda:*"]
    resources = ["arn:aws:lambda:${local.region}:${local.account_id}:function:${local.prefix}-*"]
  }

  # --- Lambda event source mapping (không giới hạn được theo tên) ---
  statement {
    sid = "LambdaEventSourceMapping"
    actions = [
      "lambda:CreateEventSourceMapping",
      "lambda:GetEventSourceMapping",
      "lambda:UpdateEventSourceMapping",
      "lambda:DeleteEventSourceMapping",
      "lambda:ListEventSourceMappings",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:ListTags",
    ]
    resources = ["*"]
  }

  # --- CloudWatch Logs ---
  statement {
    sid     = "Logs"
    actions = ["logs:*"]
    resources = [
      "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${local.prefix}-*",
      "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${local.prefix}-*:*",
    ]
  }

  statement {
    sid       = "LogsDescribe"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }

  # --- IAM role cho Lambda ---
  statement {
    sid = "IamLambdaRole"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:PutRolePolicy",
      "iam:GetRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
    ]
    resources = ["arn:aws:iam::${local.account_id}:role/${local.prefix}-*"]
  }

  # Chỉ được "giao" role đó cho dịch vụ Lambda
  statement {
    sid       = "PassRoleToLambda"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${local.account_id}:role/${local.prefix}-*"]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name   = "terraform-${local.prefix}"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_permissions.json
}
