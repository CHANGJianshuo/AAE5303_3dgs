#!/usr/bin/env python3
"""
Extract images, LiDAR, and pose data from AMtown02.bag
"""
import os
import struct
import json
import numpy as np
from pathlib import Path
from rosbags.rosbag1 import Reader
from rosbags.typesys import Stores, get_typestore

BAG_PATH = "/home/chang/5303_3dgs/AMtown02.bag"
OUTPUT_DIR = "/home/chang/5303_3dgs/AMtown02_extracted"

def main():
    os.makedirs(f"{OUTPUT_DIR}/images", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/lidar", exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/poses", exist_ok=True)

    typestore = get_typestore(Stores.ROS1_NOETIC)

    with Reader(BAG_PATH) as reader:
        # --- Stats ---
        topic_counts = {}
        for conn in reader.connections:
            topic_counts[conn.topic] = conn.msgcount
        print(f"Bag duration: {reader.duration/1e9:.1f}s")
        print(f"Images: {topic_counts.get('/left_camera/image/compressed', 0)}")
        print(f"LiDAR:  {topic_counts.get('/livox/lidar', 0)}")
        print()

        # Build connection lookup
        conn_map = {}
        for conn in reader.connections:
            if conn.topic not in conn_map:
                conn_map[conn.topic] = []
            conn_map[conn.topic].append(conn)

        # --- Extract images ---
        print("Extracting images...")
        img_count = 0
        img_timestamps = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/left_camera/image/compressed', [])
        ):
            msg = typestore.deserialize_ros1(rawdata, conn.msgtype)
            t = timestamp
            fname = f"{t}.jpg"
            with open(f"{OUTPUT_DIR}/images/{fname}", 'wb') as f:
                f.write(bytes(msg.data))
            img_timestamps.append({"index": img_count, "timestamp": int(t), "filename": fname})
            img_count += 1
            if img_count % 500 == 0:
                print(f"  {img_count} images extracted")
        print(f"  Total: {img_count} images")

        # --- Extract LiDAR point clouds ---
        print("\nExtracting LiDAR point clouds...")
        lidar_count = 0
        lidar_timestamps = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/livox/lidar', [])
        ):
            # Livox CustomMsg - save raw bytes, we'll process later
            t = timestamp
            fname = f"{t}.bin"
            with open(f"{OUTPUT_DIR}/lidar/{fname}", 'wb') as f:
                f.write(rawdata)
            lidar_timestamps.append({"index": lidar_count, "timestamp": int(t), "filename": fname})
            lidar_count += 1
            if lidar_count % 500 == 0:
                print(f"  {lidar_count} LiDAR frames extracted")
        print(f"  Total: {lidar_count} LiDAR frames")

        # --- Extract poses (attitude + position + gimbal) ---
        print("\nExtracting poses...")
        attitudes = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/dji_osdk_ros/attitude', [])
        ):
            msg = typestore.deserialize_ros1(rawdata, conn.msgtype)
            q = msg.quaternion
            attitudes.append({
                "timestamp": int(timestamp),
                "qw": float(q.w), "qx": float(q.x),
                "qy": float(q.y), "qz": float(q.z)
            })
        print(f"  Attitudes: {len(attitudes)}")

        positions = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/dji_osdk_ros/gps_position', [])
        ):
            msg = typestore.deserialize_ros1(rawdata, conn.msgtype)
            positions.append({
                "timestamp": int(timestamp),
                "latitude": float(msg.latitude),
                "longitude": float(msg.longitude),
                "altitude": float(msg.altitude)
            })
        print(f"  GPS positions: {len(positions)}")

        local_positions = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/dji_osdk_ros/local_position', [])
        ):
            msg = typestore.deserialize_ros1(rawdata, conn.msgtype)
            p = msg.point
            local_positions.append({
                "timestamp": int(timestamp),
                "x": float(p.x), "y": float(p.y), "z": float(p.z)
            })
        print(f"  Local positions: {len(local_positions)}")

        gimbal_angles = []
        for conn, timestamp, rawdata in reader.messages(
            connections=conn_map.get('/dji_osdk_ros/gimbal_angle', [])
        ):
            msg = typestore.deserialize_ros1(rawdata, conn.msgtype)
            v = msg.vector
            gimbal_angles.append({
                "timestamp": int(timestamp),
                "roll": float(v.x), "pitch": float(v.y), "yaw": float(v.z)
            })
        print(f"  Gimbal angles: {len(gimbal_angles)}")

    # Save metadata
    print("\nSaving metadata...")
    with open(f"{OUTPUT_DIR}/image_timestamps.json", 'w') as f:
        json.dump(img_timestamps, f)
    with open(f"{OUTPUT_DIR}/lidar_timestamps.json", 'w') as f:
        json.dump(lidar_timestamps, f)
    with open(f"{OUTPUT_DIR}/attitudes.json", 'w') as f:
        json.dump(attitudes, f)
    with open(f"{OUTPUT_DIR}/gps_positions.json", 'w') as f:
        json.dump(positions, f)
    with open(f"{OUTPUT_DIR}/local_positions.json", 'w') as f:
        json.dump(local_positions, f)
    with open(f"{OUTPUT_DIR}/gimbal_angles.json", 'w') as f:
        json.dump(gimbal_angles, f)

    print(f"\nDone! All data extracted to {OUTPUT_DIR}/")
    print(f"  images/     - {img_count} JPG files")
    print(f"  lidar/      - {lidar_count} binary files")
    print(f"  poses/      - attitude, GPS, local position, gimbal JSON files")

if __name__ == "__main__":
    main()
