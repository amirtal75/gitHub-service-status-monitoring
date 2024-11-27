output "github_actions_role_arn" {
  value = aws_iam_role.github_actions_role.arn
}

output "github_actions_policy_arn" {
  value = aws_iam_policy.github_actions_policy.arn
}

