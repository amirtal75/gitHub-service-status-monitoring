import boto3
import os
import sys
import json
import uuid

# Generate a unique identifier
unique_id = str(uuid.uuid4())[:8]

# AWS configuration
aws_region = 'us-west-2'
bucket_name = f'my-terraform-state-bucket-{unique_id}'
dynamodb_table_name = f'terraform-state-lock-{unique_id}'
resource_arn_file = 'resource_arns.json'
backend_tf_template_path = 'backend.tf.template'
backend_tf_path = f'{os.path.dirname(os.getcwd())}/backend.tf'

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=aws_region)
dynamodb_client = boto3.client('dynamodb', region_name=aws_region)

# Function to create S3 bucket
def create_s3_bucket(bucket_name):
    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': aws_region}
        )
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        bucket_arn = f"arn:aws:s3:::{bucket_name}"
        print(f"Success: S3 bucket '{bucket_name}' created with ARN '{bucket_arn}'.")
        return bucket_arn
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")
        sys.exit(1)

# Function to create DynamoDB table
def create_dynamodb_table(table_name):
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {'AttributeName': 'LockID', 'AttributeType': 'S'}
            ],
            KeySchema=[
                {'AttributeName': 'LockID', 'KeyType': 'HASH'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"Waiting for DynamoDB table '{table_name}' to be created...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        table_arn = dynamodb_client.describe_table(TableName=table_name)['Table']['TableArn']
        print(f"Success: DynamoDB table '{table_name}' created with ARN '{table_arn}'.")
        return table_arn
    except Exception as e:
        print(f"Error creating DynamoDB table: {e}")
        sys.exit(1)


# Function to update backend.tf.template with the generated UUID
def update_backend_tf(uuid):
    try:
        with open(backend_tf_template_path, 'r') as template_file:
            backend_tf_content = template_file.read()

        backend_tf_content = backend_tf_content.replace("12345678", uuid)

        with open(backend_tf_path, 'w') as backend_file:
            backend_file.write(backend_tf_content)

        print(f"backend.tf.template updated with UUID '{uuid}'.")
    except Exception as e:
        print(f"Error updating backend.tf.template: {e}")
        sys.exit(1)

# Main function
def main():
    # Create S3 bucket and get ARN
    bucket_arn = create_s3_bucket(bucket_name)

    # Create DynamoDB table and get ARN
    table_arn = create_dynamodb_table(dynamodb_table_name)

    # Save ARNs to a file
    resource_arns = {
        "s3_bucket_arn": bucket_arn,
        "dynamodb_table_arn": table_arn
    }
    with open(resource_arn_file, 'w') as f:
        json.dump(resource_arns, f)
    print(f"Resource ARNs saved to {resource_arn_file}.")

    # Update backend.tf.template with the generated UUID
    update_backend_tf(unique_id)

if __name__ == "__main__":
    main()
