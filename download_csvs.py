import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path

def main():
    # Create a boto3 client with unsigned configuration
    s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    bucket_name = 'asoif'
    prefix = 'warcouncil/'

    # List all objects within the warcouncil prefix
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    # Dictionary to hold the versions and their files
    version_files = {}

    # Iterate over each page and object within the warcouncil prefix
    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.csv'):
                # Extract the version number from the file path
                version = key.split('/')[1]
                if version not in version_files:
                    version_files[version] = []
                version_files[version].append(key)

    # Identify the highest version number
    highest_version = max(version_files.keys())

    # Download files from the highest version number
    local_directory_path = './warcouncil_latest_csv'

    for file_key in version_files[highest_version]:
        local_file_path = os.path.join(local_directory_path, os.path.basename(file_key))
        
        # Create directory if it doesn't exist
        if not os.path.exists(local_directory_path):
            Path(local_directory_path).mkdir(parents=True, exist_ok=True)
        
        # Download the file
        s3_client.download_file(bucket_name, file_key, local_file_path)
        print(f"Downloaded {file_key} to {local_file_path}")

if __name__ == "__main__":
    main()