resource "aws_secretsmanager_secret" "slack_app_bot_token" {
  name        = "slack_app_bot_token"
  tags = var.tags
}


resource "aws_secretsmanager_secret_version" "slack_app_bot_token_version" {
  secret_id     = aws_secretsmanager_secret.slack_app_bot_token.id
  secret_string = jsonencode({
    Token      = "update the secret with the token in aws",
  })
}

resource "aws_secretsmanager_secret" "devops_manager_phone" {
  name        = "devops_manager_phone"
  tags = var.tags
}

resource "aws_secretsmanager_secret" "director_phone" {
  name        = "director_phone"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "devops_manager_version" {
  secret_id     = aws_secretsmanager_secret.devops_manager_phone.id
  secret_string = jsonencode({
    Phone      = "update the secret with the phone in aws",
  })
}

resource "aws_secretsmanager_secret_version" "director_version" {
  secret_id     = aws_secretsmanager_secret.director_phone.id
  secret_string = jsonencode({
    Phone      = "update the secret with the phone in aws",
  })
}

resource "aws_secretsmanager_secret" "devops_manager_nickname" {
  name        = "devops_manager_nickname"
  tags = var.tags
}

resource "aws_secretsmanager_secret" "director_nickname" {
  name        = "director_nickname"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "devops_manager_nickname_version" {
  secret_id     = aws_secretsmanager_secret.devops_manager_nickname.id
  secret_string = jsonencode({
    Phone      = "update the nickname in aws",
  })
}

resource "aws_secretsmanager_secret_version" "director_nickname_version" {
  secret_id     = aws_secretsmanager_secret.director_nickname.id
  secret_string = jsonencode({
    Phone      = "update the nickname in aws",
  })
}
