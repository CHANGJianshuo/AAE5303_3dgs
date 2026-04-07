#!/usr/bin/env python3
"""
Step 2: Convert UAVScenes AMtown02 to COLMAP format
Adapted from baseline for local paths
"""
import json
import numpy as np
import struct
import os
from pathlib import Path
import shutil

DATA_DIR = "/home/chang/5303_3dgs/UAVScenes_download/interval5_CAM_LIDAR/interval5_AMtown02"
PLY_PATH = "/home/chang/5303_3dgs/AMtown02_colmap/cloud_merged.ply"
OUTPUT_DIR = "/home/chang/5303_3dgs/AMtown02_colmap"
POINT_SAMPLE_RATE = 10  # sample PLY again: 345万 -> 34.5万

def write_binary_cameras(cameras, output_path):
    with open(output_path, 'wb') as f:
        f.write(struct.pack('Q', len(cameras)))
        for camera_id, camera in cameras.items():
            f.write(struct.pack('i', camera_id))
            f.write(struct.pack('i', camera['model']))
            f.write(struct.pack('Q', camera['width']))
            f.write(struct.pack('Q', camera['height']))
            for param in camera['params']:
                f.write(struct.pack('d', param))

def write_binary_images(images, output_path):
    with open(output_path, 'wb') as f:
        f.write(struct.pack('Q', len(images)))
        for image_id, image in images.items():
            f.write(struct.pack('i', image_id))
            for q in image['qvec']:
                f.write(struct.pack('d', q))
            for t in image['tvec']:
                f.write(struct.pack('d', t))
            f.write(struct.pack('i', image['camera_id']))
            name_bytes = image['name'].encode('utf-8')
            f.write(name_bytes)
            f.write(b'\x00')
            f.write(struct.pack('Q', 0))

def write_binary_points3D(points, output_path):
    with open(output_path, 'wb') as f:
        f.write(struct.pack('Q', len(points)))
        for point_id, point in points.items():
            f.write(struct.pack('Q', point_id))
            for coord in point['xyz']:
                f.write(struct.pack('d', coord))
            for color in point['rgb']:
                f.write(struct.pack('B', color))
            f.write(struct.pack('d', point['error']))
            f.write(struct.pack('Q', 0))

def rotation_matrix_to_quaternion(R):
    trace = np.trace(R)
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (R[2, 1] - R[1, 2]) * s
        y = (R[0, 2] - R[2, 0]) * s
        z = (R[1, 0] - R[0, 1]) * s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s
    return np.array([w, x, y, z])

def load_ply_points(ply_path, sample_rate=10):
    print(f"Loading point cloud: {ply_path}")
    points = {}
    point_id = 1
    with open(ply_path, 'rb') as f:
        line = f.readline().decode('utf-8')
        while not line.startswith('end_header'):
            line = f.readline().decode('utf-8')
        sample_count = 0
        while True:
            data = f.read(15)
            if len(data) < 15:
                break
            sample_count += 1
            if sample_count % sample_rate != 0:
                continue
            x, y, z = struct.unpack('fff', data[:12])
            r, g, b = struct.unpack('BBB', data[12:15])
            points[point_id] = {
                'xyz': [x, y, z],
                'rgb': [r, g, b],
                'error': 1.0
            }
            point_id += 1
            if point_id % 50000 == 0:
                print(f"  Loaded {point_id:,} points...")
    print(f"  Total: {len(points):,} points")
    return points

def main():
    json_path = os.path.join(DATA_DIR, "sampleinfos_interpolated.json")
    images_dir = os.path.join(DATA_DIR, "interval5_CAM")

    output_path = Path(OUTPUT_DIR)
    sparse_path = output_path / "sparse" / "0"
    sparse_path.mkdir(parents=True, exist_ok=True)
    images_output = output_path / "images"
    images_output.mkdir(parents=True, exist_ok=True)

    # Load JSON
    print("[1/5] Loading pose data...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    print(f"  JSON entries: {len(data)}")

    # Get existing images
    existing_images = {f.name for f in Path(images_dir).glob("*.jpg")}
    print(f"  Images in folder: {len(existing_images)}")

    # Camera intrinsics from first matched sample
    first_sample = None
    for d in data:
        if d['OriginalImageName'] in existing_images:
            first_sample = d
            break

    P = np.array(first_sample['P3x3'])
    fx, fy = P[0, 0], P[1, 1]
    cx, cy = P[0, 2], P[1, 2]
    width = first_sample['Width']
    height = first_sample['Height']
    k1 = first_sample.get('K1', 0.0)
    k2 = first_sample.get('K2', 0.0)

    print(f"\n[2/5] Camera: {width}x{height}, fx={fx:.2f}, fy={fy:.2f}")

    cameras = {
        1: {
            'model': 4,  # OPENCV
            'width': width,
            'height': height,
            'params': [fx, fy, cx, cy, k1, k2, 0.0, 0.0]
        }
    }

    # Process image poses
    print("\n[3/5] Processing image poses...")
    images = {}
    processed = 0
    for sample in data:
        image_name = sample['OriginalImageName']
        if image_name not in existing_images:
            continue

        processed += 1
        image_id = processed

        T = np.array(sample['T4x4'])
        R = T[:3, :3]
        t = T[:3, 3]

        # T4x4 is camera-to-world, COLMAP needs world-to-camera
        R_inv = R.T
        t_inv = -R.T @ t

        qvec = rotation_matrix_to_quaternion(R_inv)

        images[image_id] = {
            'qvec': qvec.tolist(),
            'tvec': t_inv.tolist(),
            'camera_id': 1,
            'name': image_name
        }
    print(f"  Processed {processed} images")

    # Copy images
    print("\n[4/5] Copying images...")
    copied = 0
    for image_name in existing_images:
        src = Path(images_dir) / image_name
        dst = images_output / image_name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied += 1
            if copied % 200 == 0:
                print(f"  Copied {copied}/{len(existing_images)}")
    print(f"  Copied {copied} images")

    # Load 3D points
    print(f"\n[5/5] Loading point cloud (sample rate: 1/{POINT_SAMPLE_RATE})...")
    points = load_ply_points(PLY_PATH, sample_rate=POINT_SAMPLE_RATE)

    # Write COLMAP files
    print("\nWriting COLMAP binary files...")
    write_binary_cameras(cameras, sparse_path / "cameras.bin")
    print("  cameras.bin")
    write_binary_images(images, sparse_path / "images.bin")
    print("  images.bin")
    write_binary_points3D(points, sparse_path / "points3D.bin")
    print("  points3D.bin")

    print(f"\nDone! Output: {OUTPUT_DIR}")
    print(f"  {len(cameras)} camera(s)")
    print(f"  {len(images)} images")
    print(f"  {len(points):,} 3D points")
    print(f"\nReady for OpenSplat:")
    print(f"  ./opensplat {OUTPUT_DIR} -n 30000 -o amtown02_output.ply")

if __name__ == "__main__":
    main()
