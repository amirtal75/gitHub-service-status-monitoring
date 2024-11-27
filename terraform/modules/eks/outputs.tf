output "cluster_id" {
  value = aws_eks_cluster.eks_cluster.id
}

output "node_group_id" {
  value = aws_eks_node_group.node_group.id
}

output "cluster_endpoint" {
  value = aws_eks_cluster.eks_cluster.endpoint
}

output "cluster_certificate_authority_data" {
  value = aws_eks_cluster.eks_cluster.certificate_authority.0.data
}

output "cluster_name" {
  value = aws_eks_cluster.eks_cluster.name
}

output "monitoring_security_group_arn" {
  value = aws_security_group.monitoring_security_group
}

output "cluster_oidc" {
  value = aws_eks_cluster.eks_cluster.identity[0].oidc[0].issuer
}