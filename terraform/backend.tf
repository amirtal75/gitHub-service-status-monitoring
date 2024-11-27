
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket-4cb48d9f"
    key            = "terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-state-lock-4cb48d9f"
  }
}
