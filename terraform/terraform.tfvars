aws_region                            = "us-west-2"
vpc_cidr                              = "10.0.0.0/16"
public_subnet_a_cidr                  = "10.0.1.0/24"
public_subnet_b_cidr                  = "10.0.2.0/24"
private_subnet_a_cidr                 = "10.0.3.0/24"
private_subnet_b_cidr                 = "10.0.4.0/24"
availability_zone_a                   = "us-west-2a"
availability_zone_b                   = "us-west-2b"
eks_cluster_name                      = "monitoring"
node_group_name                       = "monitoring-node-group"
desired_size                          = 2
max_size                              = 2
min_size                              = 1
my_terraform_plan_block_apply_bucket  = "my-terraform-plan-block-apply-bucket"
aws_iam_eks_group_name                = "eks_access"
aws_iam_eks_user                      = "eks_user"
