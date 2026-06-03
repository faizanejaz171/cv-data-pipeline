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

def load_manifest(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}

def upload_videos_to_storage():
    # Load configuration from project root
    config_path = ROOT_DIR / "configs" / "pipeline_config.yaml"
    if not config_path.exists():
        print(f"❌ Error: Config file not found at {config_path}")
        sys.exit(1)
        
    with open(config_path) as f:
        config = yaml.safe_load(f)
        
    cfg_rec = config["recording"]
    
    # Resolve absolute paths to prevent any terminal location issue
    recordings_dir = ROOT_DIR / cfg_rec["output_dir"]
    manifest_path = ROOT_DIR / "data" / "uploaded_manifest.json"
    
    print(f"[System] Scanning directory: {recordings_dir}")
    
    manifest = load_manifest(manifest_path)
    videos = list(recordings_dir.glob("*.mp4"))
    
    if not videos:
        print("❌ No .mp4 videos found in recordings directory to upload.")
        return

    uploaded_count = 0
    for video_path in videos:
        file_key = video_path.name
        
        # Idempotency Gate Check
        if file_key in manifest:
            print(f"ℹ️ {file_key} already uploaded previously. Skipping.")
            continue
            
        print(f"🚀 Uploading {file_key} to MinIO bucket 'cv-recordings'...")
        
        try:
            # Uploading directly to local cloud storage simulator
            s3_client.upload_file(str(video_path), "cv-recordings", file_key)
            
            # Update history manifest file
            manifest[file_key] = {
                "status": "uploaded",
                "size_mb": round(video_path.stat().st_size / (1024**2), 2),
                "timestamp": file_key.split('_')[-1].replace('.mp4', '')
            }
            uploaded_count += 1
            print(f"✅ Successfully uploaded: {file_key}")
            
        except Exception as e:
            print(f"❌ Error uploading {file_key}: {str(e)}")

    # Write manifest back to data/ folder
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n🎉 Session Finished. Total {uploaded_count} new files uploaded to simulator.")

if __name__ == "__main__":
    upload_videos_to_storage()
