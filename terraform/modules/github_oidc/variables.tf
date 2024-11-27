variable "aws_region" {
  description = "AWS region"
  type        = string
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
}

variable "github_actions_policy_name" {
  description = "IAM Policy name for GitHub Actions"
  type        = string
}

variable "cluster_oidc" {
  description = "IAM Policy name for GitHub Actions"
  type        = string
}

