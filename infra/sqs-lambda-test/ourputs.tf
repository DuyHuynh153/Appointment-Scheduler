output "queue_url" {
  value = aws_sqs_queue.main.url
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "lambda_name" {
  value = aws_lambda_function.fn.function_name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.fn.name
}
