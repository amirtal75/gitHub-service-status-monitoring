variable "aws_region" {
  description = "AWS region"
  type        = string
}
variable "aws_iam_eks_group_name" {
  description = "Name of an IAM group with access to the eks cluster"
  type        = string
}

variable "aws_iam_eks_user" {
  description = "user to be a member of aws_iam_eks_group_name"
  type        = string
}