#!/usr/bin/env python3
"""
Step 1: Merge LiDAR txt files to PLY point cloud
Adapted from baseline for local paths
"""
import numpy as np
import struct
import os
from pathlib import Path

LIDAR_DIR = "/home/chang/5303_3dgs/UAVScenes_download/interval5_CAM_LIDAR/interval5_AMtown02/interval5_LIDAR"
OUTPUT_PLY = "/home/chang/5303_3dgs/AMtown02_colmap/cloud_merged.ply"
SAMPLE_RATE = 10  # keep every 10th point: 3450万 -> 345万

def write_ply_header(f, num_points):
    header = f"""ply
format binary_little_endian 1.0
element vertex {num_points}
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
end_header
"""
    f.write(header.encode('ascii'))

def main():
    os.makedirs(os.path.dirname(OUTPUT_PLY), exist_ok=True)

    lidar_path = Path(LIDAR_DIR)
    txt_files = sorted(lidar_path.glob("*.txt"))
    print(f"Found {len(txt_files)} LiDAR files")
    print(f"Sample rate: 1/{SAMPLE_RATE}")

    # First pass: count points
    print("\n[1/2] Counting points...")
    total_points = 0
    for txt_file in txt_files:
        with open(txt_file, 'r') as f:
            num_lines = sum(1 for _ in f)
            total_points += (num_lines + SAMPLE_RATE - 1) // SAMPLE_RATE
    print(f"Total points after sampling: {total_points:,}")

    # Second pass: write PLY
    print("\n[2/2] Writing PLY...")
    with open(OUTPUT_PLY, 'wb') as f:
        write_ply_header(f, total_points)

        points_written = 0
        for i, txt_file in enumerate(txt_files):
            with open(txt_file, 'r') as txt_f:
                for line_idx, line in enumerate(txt_f):
                    if line_idx % SAMPLE_RATE != 0:
                        continue
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    try:
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        f.write(struct.pack('fff', x, y, z))
                        f.write(struct.pack('BBB', 128, 128, 128))
                        points_written += 1
                    except (ValueError, IndexError):
                        continue
            if (i + 1) % 200 == 0:
                print(f"  Processed {i+1}/{len(txt_files)} files ({points_written:,} points)")

    size_mb = os.path.getsize(OUTPUT_PLY) / (1024**2)
    print(f"\nDone! {points_written:,} points -> {OUTPUT_PLY} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    main()
