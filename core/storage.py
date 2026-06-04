# core/storage.py
import os
import logging
from dotenv import load_dotenv
import boto3
from botocore.exceptions import EndpointConnectionError, ClientError

load_dotenv()
logger = logging.getLogger("core_storage")
logging.basicConfig(level=logging.INFO)

# MinIO Configs
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "marketing-assets")
# Public URL for browser access
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

logger.info(f"Attempting to connect to MinIO S3 at {MINIO_ENDPOINT}...")

# Configure boto3 client
# Clean endpoint format
endpoint_url = MINIO_ENDPOINT
if not endpoint_url.startswith("http://") and not endpoint_url.startswith("https://"):
    endpoint_url = f"http://{endpoint_url}"
    
s3_client = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=boto3.session.Config(signature_version="s3v4")
)

# Try listing buckets to check connection
s3_client.list_buckets()

# Auto-create bucket if missing
try:
    s3_client.head_bucket(Bucket=MINIO_BUCKET)
except ClientError:
    logger.info(f"Bucket '{MINIO_BUCKET}' does not exist. Creating bucket...")
    s3_client.create_bucket(Bucket=MINIO_BUCKET)
    
logger.info(f"Successfully connected to MinIO S3! Default bucket: '{MINIO_BUCKET}'")

def upload_file(local_file_path: str, object_key: str, bucket_name: str = None) -> str:
    """
    Upload a file to MinIO S3.
    Returns the file URL.
    """
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"Source file not found at: {local_file_path}")
        
    bucket = bucket_name or MINIO_BUCKET
        
    try:
        # Auto-create bucket if missing
        try:
            s3_client.head_bucket(Bucket=bucket)
        except ClientError:
            logger.info(f"Bucket '{bucket}' does not exist. Creating bucket...")
            s3_client.create_bucket(Bucket=bucket)

        logger.info(f"Uploading {local_file_path} to S3 bucket '{bucket}' with key '{object_key}'...")
        s3_client.upload_file(local_file_path, bucket, object_key)
        
        # Generate pre-signed URL or public URL
        clean_public_endpoint = MINIO_PUBLIC_URL
        if not clean_public_endpoint.startswith("http://") and not clean_public_endpoint.startswith("https://"):
            clean_public_endpoint = f"http://{clean_public_endpoint}"
            
        file_url = f"{clean_public_endpoint}/{bucket}/{object_key}"
        logger.info(f"File uploaded successfully! S3 URL: {file_url}")
        return file_url
    except Exception as e:
        logger.error(f"S3 Upload failed for bucket '{bucket}': {e}")
        raise e

def download_file_from_minio(object_key: str, dest_path: str) -> str:
    """
    Download file từ MinIO S3 về local path.
    Dùng bởi Celery worker để lấy file gốc về xử lý embedding.

    Returns: dest_path sau khi download thành công.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    try:
        logger.info(f"[storage] Downloading s3://{MINIO_BUCKET}/{object_key} → {dest_path}")
        s3_client.download_file(MINIO_BUCKET, object_key, dest_path)
        logger.info(f"[storage] Download OK: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"[storage] MinIO download failed: {e}")
        raise e
