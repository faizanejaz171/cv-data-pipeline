import json
import yaml
import logging
import boto3
import sys
from pathlib import Path

# Automatically detect project root directory (cv-data-pipeline/)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

# Local MinIO Cloud Simulator Connection
s3_client = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="password123"
)

def download_new_videos():
    # Load configuration from project root
    config_path = ROOT_DIR / "configs" / "pipeline_config.yaml"
    if not config_path.exists():
        print(f"❌ Error: Config file not found at {config_path}")
        sys.exit(1)
        
    with open(config_path) as f:
        config = yaml.safe_load(f)
        
    cfg_sim = config["gcp_simulation"]
    
    # Target directory jahan cloud se video download hogi
    download_dir = ROOT_DIR / cfg_sim["local_download_dir"]
    download_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[System] Checking virtual cloud bucket 'cv-recordings' for new files...")
    
    try:
        # Bucket ki saari files ki list nikalna
        response = s3_client.list_objects_v2(Bucket="cv-recordings")
        
        if "Contents" not in response:
            print("ℹ️ Cloud bucket is completely empty. Nothing to download.")
            return
            
        downloaded_count = 0
        
        for obj in response["Contents"]:
            file_name = obj["Key"]
            dest_path = download_dir / file_name
            
            # Idempotency Gate Check: Agar file pehle se downloaded hai toh skip karo
            if dest_path.exists():
                print(f"ℹ️ File {file_name} already exists locally in downloaded folder. Skipping.")
                continue
                
            print(f"📥 Downloading {file_name} from virtual cloud storage...")
            s3_client.download_file("cv-recordings", file_name, str(dest_path))
            print(f"✅ Successfully downloaded: {file_name}")
            downloaded_count += 1
            
        print(f"\n🎉 Session Finished. Total {downloaded_count} new files downloaded.")
        
    except Exception as e:
        print(f"❌ Error during download process: {str(e)}")

if __name__ == "__main__":
    download_new_videos()
