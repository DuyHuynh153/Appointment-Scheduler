locals {
  name = var.name_prefix
}

# ---------------------------------------------------------------
# SQS: Dead-letter queue (nơi chứa tin nhắn xử lý lỗi nhiều lần)
# ---------------------------------------------------------------
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name}-dlq"
  message_retention_seconds = 345600 # 4 ngày
  sqs_managed_sse_enabled   = true   # mã hoá miễn phí
}

# ---------------------------------------------------------------
# SQS: Main queue
# ---------------------------------------------------------------
resource "aws_sqs_queue" "main" {
  name                       = "${local.name}-queue"
  visibility_timeout_seconds = var.lambda_timeout * 6 # AWS khuyến nghị >= 6x Lambda timeout
  receive_wait_time_seconds  = 20                     # long polling, giảm số request rỗng
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

# ---------------------------------------------------------------
# CloudWatch log group: tạo tường minh để
# (1) có retention, (2) bị xoá khi terraform destroy
# ---------------------------------------------------------------
resource "aws_cloudwatch_log_group" "fn" {
  name              = "/aws/lambda/${local.name}-fn" # phải khớp function_name bên dưới
  retention_in_days = 7
}

# ---------------------------------------------------------------
# IAM role cho Lambda
# ---------------------------------------------------------------
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "fn" {
  name               = "${local.name}-fn-role" # khớp prefix CI role được phép tạo
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "fn" {
  # Đọc/xoá tin nhắn: CHỈ trên main queue
  statement {
    sid = "ConsumeQueue"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.main.arn]
  }

  # Ghi log: CHỈ vào log group của nó
  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.fn.arn}:*"]
  }
}

resource "aws_iam_role_policy" "fn" {
  name   = "consume-queue-and-log"
  role   = aws_iam_role.fn.id
  policy = data.aws_iam_policy_document.fn.json
}

# ---------------------------------------------------------------
# Đóng gói code Lambda (handler chỉ dùng thư viện chuẩn, không cần pip)
# ---------------------------------------------------------------
data "archive_file" "fn" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambdas/sqs_test"
  output_path = "${path.module}/build/sqs_test.zip"
}

# ---------------------------------------------------------------
# Lambda function
# ---------------------------------------------------------------
resource "aws_lambda_function" "fn" {
  function_name    = "${local.name}-fn"
  role             = aws_iam_role.fn.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler" # <file>.<hàm>
  filename         = data.archive_file.fn.output_path
  source_code_hash = data.archive_file.fn.output_base64sha256 # code đổi thì redeploy
  memory_size      = 128
  timeout          = var.lambda_timeout

  # Đảm bảo quyền và log group có trước khi Lambda chạy
  depends_on = [
    aws_iam_role_policy.fn,
    aws_cloudwatch_log_group.fn,
  ]
}

# ---------------------------------------------------------------
# Nối SQS → Lambda
# ---------------------------------------------------------------
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.fn.arn
  batch_size       = 10

  # Cho phép Lambda báo "chỉ message X lỗi", không retry cả batch
  function_response_types = ["ReportBatchItemFailures"]

  # Giới hạn số Lambda chạy song song (tối thiểu là 2)
  scaling_config {
    maximum_concurrency = 2
  }
}
