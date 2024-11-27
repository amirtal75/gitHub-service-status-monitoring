output "random_id" {
  value = random_id.bucket_suffix.hex
}
output "monitoring_security_group_arn" {
  value = module.eks.monitoring_security_group_arn.id
}

output "cluster_oidc" {
  value = module.eks.cluster_oidc
}

