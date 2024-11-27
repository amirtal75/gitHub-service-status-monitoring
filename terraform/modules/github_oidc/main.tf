# resource "aws_iam_role" "github_actions_role" {
#   name = var.github_actions_role_name
#
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Effect = "Allow",
#         Principal = {
#           Federated = aws_iam_openid_connect_provider.github.arn
#         },
#         Action = "sts:AssumeRoleWithWebIdentity",
#         Condition = {
#           StringEquals = {
#             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
#             "token.actions.githubusercontent.com:sub": "repo:${var.github_username}/${var.github_repo_name}:ref:refs/heads/main"
#           }
#         }
#       }
#     ]
#   })
# }

resource "aws_iam_policy" "github_actions_policy" {
  name        = var.github_actions_policy_name
  description = "Policy for GitHub Actions to deploy to AWS"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:*",
          "ec2:*",
          "eks:*",
          "dynamodb:*",
          "iam:*",
          "sqs:*",
          "sns:*",
          "secretsmanager:*"
        ],
        Resource = "*"
      }
    ]
  })
}

locals {
  cluster_oidc_id = regex("id/([a-zA-Z0-9]+)$", var.cluster_oidc)[0]
}

resource "aws_iam_role" "github_actions_role" {
  name = var.github_actions_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # GitHub OIDC Trust Relationship
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": "repo:${var.github_username}/${var.github_repo_name}:ref:refs/heads/main"
          }
        }
      },
      {
        # EKS OIDC Trust Relationship for all service accounts in the cluster
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks.arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringLike = {
            "oidc.eks.${var.aws_region}.amazonaws.com/id/${local.cluster_oidc_id}:sub": "system:serviceaccount:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_openid_connect_provider" "github" {
  url                   = "https://token.actions.githubusercontent.com"
  client_id_list        = ["sts.amazonaws.com"]
  thumbprint_list       = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = ["9e99a48a9960a6cc57eec7df47945c7da8e34de6"]
  url = var.cluster_oidc
}


resource "aws_iam_role_policy_attachment" "github_actions_attachment" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.github_actions_policy.arn
}

resource "aws_iam_role_policy_attachment" "eks_service_policy" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
}
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}
resource "aws_iam_role_policy_attachment" "eks_node_policy" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}


