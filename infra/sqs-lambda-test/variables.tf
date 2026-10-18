variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "name_prefix" {
  description = "Must match the prefix the CI role is allowed to manage (see bootstrap)"
  type        = string
  default     = "sqs-lambda-test"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 10
}

variable "max_receive_count" {
  description = "Failed receives before a message is moved to the DLQ"
  type        = number
  default     = 3
}
