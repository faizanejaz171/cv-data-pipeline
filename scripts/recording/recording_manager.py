import subprocess
import os
import shutil
import logging
import yaml
import sys
from datetime import datetime
from pathlib import Path

def load_config(path="configs/pipeline_config.yaml"):
    """YAML config file ko load karne ka function"""
    with open(path) as f:
        return yaml.safe_load(f)

def get_free_disk_gb(path):
    """Computer ki free disk space (GB mein) check karne ka function"""
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)

def rotate_old_recordings(output_dir, min_free_gb):
    """Agar disk space kam ho toh purani mp4 files delete karne ka function"""
    files = sorted(Path(output_dir).glob("*.mp4"), key=os.path.getmtime)
    while get_free_disk_gb(output_dir) < min_free_gb and files:
        oldest = files.pop(0)
        logging.warning(f"Low Disk Space! Deleting oldest recording: {oldest}")
        oldest.unlink()

def check_scheduling_gate(config):
    """Date aur Time check karne ka brain (Gate Engine)"""
    sched = config.get("scheduling", {})
    if not sched.get("one_time_job", False):
        return True # Agar normal job hai toh chalne do
    
    # Aaj ki tareek aur abhi ka ghanta nikalna
    current_date = datetime.now().strftime("%Y-%m-%d") # Format: 2026-06-01
    current_hour = datetime.now().hour                # Format: 1
    
    target_date = sched.get("target_date")
    start_hour = sched.get("start_hour")
    end_hour = sched.get("end_hour")
    
    # 1. Date Check: Agar tareek match nahi karti toh band ho jao
    if current_date != target_date:
        logging.info(f"Execution skipped: Current date {current_date} does not match target date {target_date}.")
        return False
        
    # 2. Time Window Check: Agar hour start_hour se kam ya end_hour se zyada hai toh band ho jao
    if current_hour < start_hour or current_hour >= end_hour:
        logging.info(f"Execution skipped: Current hour {current_hour} is outside the [{start_hour}-{end_hour}] window.")
        return False
        
    return True

def record_camera_stream(config):
    cfg = config["recording"]
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Time Gate Trigger Check
    if not check_scheduling_gate(config):
        print("Gate Closed: Conditions not met. Exiting safely.")
        sys.exit(0)

    # 2. Disk Space Safety Check
    free_gb = get_free_disk_gb(str(output_dir))
    if free_gb < cfg["min_free_disk_gb"]:
        logging.warning(f"Low disk detected: {free_gb:.1f}GB free. Rotating files...")
        rotate_old_recordings(str(output_dir), cfg["min_free_disk_gb"])

    # 3. Output File Ka Naam Generate Karna (Client Name + Timestamp)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client_name = config["client"]["name"]
    filename = output_dir / f"{client_name}_{timestamp}.mp4"

    # 4. FFmpeg Production Command Formulation
    cmd = [
        "ffmpeg", "-y",                # Overwrite file agar pehle se exist karti ho
        "-rtsp_transport", "tcp",      # RTSP stream ko stable rakhne ke liye over TCP
        "-i", cfg["source"],           # Camera ka link
        "-t", str(cfg["chunk_duration_seconds"]), # Kitne seconds record karna hai (3600 seconds)
        "-c:v", "copy",                # Video re-encode na karein (No CPU load, super fast)
        "-an",                         # Audio record nahi karni (No sound)
        str(filename)
    ]
    
    logging.info(f"Starting 1-Hour Recording from camera stream: {filename}")
    
    # FFmpeg process ko background mein run karna
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        size_mb = filename.stat().st_size / (1024**2)
        logging.info(f"Successfully recorded {filename.name} ({size_mb:.1f} MB)")
        print(f"✅ Success: File saved at {filename}")
    else:
        error_msg = result.stderr.decode()
        logging.error(f"FFmpeg process failed: {error_msg}")
        print(f"❌ Error: FFmpeg failed. Check logs at {cfg['log_file']}")

if __name__ == "__main__":
    config = load_config()
    
    # Logging configuration setup
    log_file_path = config["recording"]["log_file"]
    Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    
    record_camera_stream(config)
