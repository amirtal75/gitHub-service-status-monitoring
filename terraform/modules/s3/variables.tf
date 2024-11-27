variable "my_terraform_plan_block_apply_bucket" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "retention_hours" {
  description = "The number of hours to retain objects in the bucket"
  type        = number
  default     = 3
}

variable "tags" {
  description = "A map of tags to assign to the bucket"
  type        = map(string)
  default     = {}
}

variable "sre_bucket" {
  description = "The name of the S3 bucket"
  type        = string
}
