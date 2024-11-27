output "bucket_name" {
  value = aws_s3_bucket.this.id
}

output "sre_bucket_name" {
  description = "The name of the SRE bucket"
  value       = aws_s3_bucket.sre.id
}

output "bucket_arn" {
  description = "The ARN of the plan/apply bucket"
  value       = aws_s3_bucket.this.arn
}

output "sre_bucket_arn" {
  description = "The ARN of the plan/apply bucket"
  value       = aws_s3_bucket.sre.arn
}