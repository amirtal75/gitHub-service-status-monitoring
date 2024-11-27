import boto3
import json
import sys
import os

# AWS configuration
aws_region = 'us-west-2'
resource_arn_file = 'resource_arns.json'

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=aws_region)
dynamodb_client = boto3.client('dynamodb', region_name=aws_region)


# Function to print AWS CLI commands to delete all versions and markers in the S3 bucket
def print_delete_commands(bucket_name):
    try:
        versions = s3_client.list_object_versions(Bucket=bucket_name)
        delete_markers = versions.get('DeleteMarkers', [])
        versions_list = versions.get('Versions', [])

        delete_commands = []

        for delete_marker in delete_markers:
            command = f"aws s3api delete-object --bucket {bucket_name} --key {delete_marker['Key']} --version-id {delete_marker['VersionId']}"
            delete_commands.append(command)

        for version in versions_list:
            command = f"aws s3api delete-object --bucket {bucket_name} --key {version['Key']} --version-id {version['VersionId']}"
            delete_commands.append(command)

        if delete_commands:
            print(
                f"S3 bucket '{bucket_name}' is not empty. Use the following AWS CLI commands to delete all files and versions:")
            for command in delete_commands:
                print(command)
        else:
            print(f"No versions or delete markers found in bucket '{bucket_name}'.")
    except Exception as e:
        print(f"Error generating delete commands for S3 bucket: {e}")
        sys.exit(1)


# Function to delete S3 bucket and its contents
def delete_s3_bucket(bucket_name):
    try:
        # Check if bucket is empty
        response = s3_client.list_object_versions(Bucket=bucket_name)
        if 'DeleteMarkers' in response or 'Versions' in response:
            print_delete_commands(bucket_name)
        else:
            # Delete the bucket
            s3_client.delete_bucket(Bucket=bucket_name)
            waiter = s3_client.get_waiter('bucket_not_exists')
            waiter.wait(Bucket=bucket_name)
            print(f"Success: S3 bucket '{bucket_name}' deleted.")
    except Exception as e:
        print(f"Error deleting S3 bucket: {e}")
        sys.exit(1)


# Function to delete DynamoDB table
def delete_dynamodb_table(table_name):
    try:
        dynamodb_client.delete_table(TableName=table_name)
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        print(f"Success: DynamoDB table '{table_name}' deleted.")
    except Exception as e:
        print(f"Error deleting DynamoDB table: {e}")
        sys.exit(1)


# Main function
def main():
    # Load ARNs from file
    if not os.path.exists(resource_arn_file):
        print(f"Error: {resource_arn_file} does not exist.")
        sys.exit(1)

    with open(resource_arn_file, 'r') as f:
        resource_arns = json.load(f)

    s3_bucket_arn = resource_arns.get("s3_bucket_arn")
    dynamodb_table_arn = resource_arns.get("dynamodb_table_arn")

    if not s3_bucket_arn or not dynamodb_table_arn:
        print("Error: Invalid ARNs in resource ARN file.")
        sys.exit(1)

    # Delete S3 bucket
    bucket_name = s3_bucket_arn.split(":::")[1]
    delete_s3_bucket(bucket_name)

    # Delete DynamoDB table
    table_name = dynamodb_table_arn.split(":table/")[1]
    delete_dynamodb_table(table_name)


if __name__ == "__main__":
    main()
