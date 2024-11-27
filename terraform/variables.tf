variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_a_cidr" {
  description = "CIDR block for the public subnet in AZ a"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_b_cidr" {
  description = "CIDR block for the public subnet in AZ b"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_subnet_a_cidr" {
  description = "CIDR block for the private subnet in AZ a"
  type        = string
  default     = "10.0.3.0/24"
}

variable "private_subnet_b_cidr" {
  description = "CIDR block for the private subnet in AZ b"
  type        = string
  default     = "10.0.4.0/24"
}

variable "availability_zone_a" {
  description = "Availability Zone a"
  type        = string
  default     = "us-west-2a"
}

variable "availability_zone_b" {
  description = "Availability Zone b"
  type        = string
  default     = "us-west-2b"
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "MonitoringClusterTest"
}

variable "node_group_name" {
  description = "Name of the EKS node group"
  type        = string
  default     = "Monitoring-node-group"
}

variable "desired_size" {
  description = "Desired size of the EKS node group"
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum size of the EKS node group"
  type        = number
  default     = 2
}

variable "min_size" {
  description = "Minimum size of the EKS node group"
  type        = number
  default     = 1
}

variable "github_username" {
  description = "GitHub username or organization"
  type        = string
}

variable "github_repo_name" {
  description = "GitHub repository name"
  type        = string
}

variable "github_actions_role_name" {
  description = "IAM Role name for GitHub Actions"
  type        = string
  default     = "github-actions-role"
}

variable "github_actions_policy_name" {
  description = "IAM Policy name for GitHub Actions"
  type        = string
  default     = "github-actions-policy"
}

variable "my_terraform_plan_block_apply_bucket" {
  description = "Bucket for overriding github download and upload artifact to implement a uuid based terraform-plan and apply-"
  type        = string
  default     = "my-terraform-plan-block-apply-bucket"
}

variable "aws_iam_eks_group_name" {
  description = "Name of an IAM group with access to the eks cluster"
  type        = string
  default     = "eks_access"
}

variable "aws_iam_eks_user" {
  description = "user to be a member of aws_iam_eks_group_name"
  type        = string
  default     = "eks_user"
}

variable "sre_bucket" {
  description = "Bucket for overriding github download and upload artifact to implement a uuid based terraform-plan and apply-"
  type        = string
  default     = "sre"
}