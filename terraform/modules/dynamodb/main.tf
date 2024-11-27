resource "aws_dynamodb_table" "github_table_name" {
  billing_mode = "PAY_PER_REQUEST"
  name         = var.github_table_name
  hash_key     = "incident_id" # Partition key

  # Attributes
  attribute {
    name = "incident_id"
    type = "S" # String type
  }

#   attribute {
#     name = "down_services"
#     type = "S" # JSON string representing the list of affected services
#   }
#
#   attribute {
#     name = "creation_date"
#     type = "S" # String to store ISO 8601 formatted date
#   }
#
#   attribute {
#     name = "resolved_date"
#     type = "S" # Optional, stores resolution date
#   }
#
#   attribute {
#     name = "closed_date"
#     type = "S" # Optional, stores closure date
#   }
#
  attribute {
    name = "status"
    type = "S" # Current status of the incident
  }
#
#   attribute {
#     name = "escalation_status"
#     type = "S" # Tracks escalation status (e.g., 'Not Escalated', 'Escalated')
#   }

  # Optional: Add status_history as JSON string (handled at application level)
  # This attribute is not indexed directly but stored and managed by the app.
#   attribute {
#     name = "status_history"
#     type = "S" # JSON string with status and update timestamps
#   }

  # Global Secondary Index (GSI) for querying by status
  global_secondary_index {
    name               = "status-index"
    hash_key           = "status"
    projection_type    = "ALL"
  }

  tags = {
    Environment = "Production"
    Application = "GitHub Monitoring"
  }
}

resource "aws_dynamodb_table" "cyberark_table_name" {
  billing_mode = "PAY_PER_REQUEST"
  name         = var.cyberark_table_name
  hash_key     = "incident_id" # Partition key

  # Attributes
  attribute {
    name = "incident_id"
    type = "S" # String type
  }

  attribute {
    name = "status"
    type = "S" # Current status of the incident
  }

  # Global Secondary Index (GSI) for querying by status
  global_secondary_index {
    name               = "status-index"
    hash_key           = "status"
    projection_type    = "ALL"
  }

  tags = {
    Environment = "Production"
    Application = "GitHub Monitoring"
  }
}

resource "aws_dynamodb_table" "test_cyberark_table_name" {
  billing_mode = "PAY_PER_REQUEST"
  name         = var.test_cyberark_table_name
  hash_key     = "incident_id" # Partition key

  # Attributes
  attribute {
    name = "incident_id"
    type = "S" # String type
  }

  attribute {
    name = "status"
    type = "S" # Current status of the incident
  }

  # Global Secondary Index (GSI) for querying by status
  global_secondary_index {
    name               = "status-index"
    hash_key           = "status"
    projection_type    = "ALL"
  }

  tags = {
    Environment = "Test"
    Application = "GitHub Monitoring"
  }
}

resource "aws_dynamodb_table" "test_github_table_name" {
  billing_mode = "PAY_PER_REQUEST"
  name         = var.test_github_table_name
  hash_key     = "incident_id" # Partition key

  # Attributes
  attribute {
    name = "incident_id"
    type = "S" # String type
  }

  attribute {
    name = "status"
    type = "S" # Current status of the incident
  }

  # Global Secondary Index (GSI) for querying by status
  global_secondary_index {
    name               = "status-index"
    hash_key           = "status"
    projection_type    = "ALL"
  }

  tags = {
    Environment = "Test"
    Application = "GitHub Monitoring"
  }
}

