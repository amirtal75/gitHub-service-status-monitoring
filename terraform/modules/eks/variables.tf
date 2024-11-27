variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "node_group_name" {
  description = "Name of the EKS node group"
  type        = string
}

variable "desired_size" {
  description = "Desired size of the EKS node group"
  type        = number
}

variable "max_size" {
  description = "Maximum size of the EKS node group"
  type        = number
}

variable "min_size" {
  description = "Minimum size of the EKS node group"
  type        = number
}

variable "subnet_ids" {
  description = "Subnets for the EKS cluster"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID for the EKS cluster"
  type        = string
}

variable "cluster_role_arn" {
  description = "ARN of the EKS Cluster IAM Role"
  type        = string
}

variable "node_role_arn" {
  description = "ARN of the EKS Node IAM Role"
  type        = string
}

variable "github_actions_role_arn" {
  description = "The ARN of the GitHub Actions role"
  type        = string
}
