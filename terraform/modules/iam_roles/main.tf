resource "aws_iam_group" "eks_access" {
  name = var.aws_iam_eks_group_name
}

resource "aws_iam_group_policy_attachment" "eks_cluster_policy" {
  group      = aws_iam_group.eks_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_group_policy_attachment" "eks_worker_node_policy" {
  group      = aws_iam_group.eks_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_group_policy_attachment" "sqs_read_only_access" {
  group      = aws_iam_group.eks_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSQSReadOnlyAccess"
}

resource "aws_iam_group_policy_attachment" "lambda_full_access" {
  group      = aws_iam_group.eks_access.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
}

resource "aws_iam_user" "eks_user" {
  name = var.aws_iam_eks_user
}

resource "aws_iam_user_group_membership" "eks_user_membership" {
  user = aws_iam_user.eks_user.name
  groups = [
    aws_iam_group.eks_access.name
  ]
}

resource "aws_iam_role" "eks_cluster_role" {
  name = "eks_cluster_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "eks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
}

resource "aws_iam_role" "eks_node_role" {
  name = "eks_node_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ec2_container_registry_read_only" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Dynamically fetch the account ID
data "aws_caller_identity" "current" {}

# Create a custom policy for DynamoDB access
resource "aws_iam_policy" "dynamodb_policy" {
  name        = "DynamoDBAccessPolicy"
  description = "Policy for accessing GitHub and CyberArk DynamoDB tables"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ],
        Resource = [
          "arn:aws:dynamodb:us-west-2:${data.aws_caller_identity.current.account_id}:table/GithubIncidents",
          "arn:aws:dynamodb:us-west-2:${data.aws_caller_identity.current.account_id}:table/CyberArkIncidents"
        ]
      }
    ]
  })
}

# Attach the policy to the EKS Node Role (or another appropriate role)
resource "aws_iam_role_policy_attachment" "dynamodb_policy_attachment" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = aws_iam_policy.dynamodb_policy.arn
}
# ttach the policy to the EKS Cluster Role
resource "aws_iam_role_policy_attachment" "dynamodb_policy_attachment_cluster_role" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = aws_iam_policy.dynamodb_policy.arn
}

# Attach the policy to the IAM group if relevant
resource "aws_iam_group_policy_attachment" "dynamodb_policy_attachment_group" {
  group      = aws_iam_group.eks_access.name
  policy_arn = aws_iam_policy.dynamodb_policy.arn
}
