#!/bin/bash
# =============================================================
# AMtown02 3D Gaussian Splatting Training Script
# Hardware: NVIDIA A100 PCIe 40GB
# Data: 1,380 images (2448x2048), 343,815 initial points
# =============================================================

# Path to OpenSplat binary (adjust after building on A100)
OPENSPLAT="./opensplat"
DATA_DIR="/path/to/AMtown02_colmap"  # adjust to A100 path

# =============================================================
# Option 1: Quick Test (verify data is correct)
# Expected: ~5-10 min, rough quality
# =============================================================
# ${OPENSPLAT} ${DATA_DIR} \
#     -n 7000 \
#     -d 2 \
#     --sh-degree 2 \
#     --ssim-weight 0.2 \
#     --refine-every 100 \
#     --warmup-length 500 \
#     -o amtown02_quick_test.ply \
#     2>&1 | tee train_quick.log

# =============================================================
# Option 2: Standard Training (recommended)
# Expected: ~30-60 min, high quality
# =============================================================
${OPENSPLAT} ${DATA_DIR} \
    -n 30000 \
    -d 1 \
    --sh-degree 3 \
    --sh-degree-interval 1000 \
    --ssim-weight 0.2 \
    --refine-every 100 \
    --warmup-length 500 \
    --densify-grad-thresh 0.0002 \
    --densify-size-thresh 0.01 \
    --reset-alpha-every 30 \
    --num-downscales 2 \
    --resolution-schedule 3000 \
    --save-every 5000 \
    --val \
    -o amtown02_30k.ply \
    2>&1 | tee train_30k.log

# =============================================================
# Option 3: Maximum Quality
# Expected: ~60-90 min, best quality
# =============================================================
# ${OPENSPLAT} ${DATA_DIR} \
#     -n 30000 \
#     -d 1 \
#     --sh-degree 3 \
#     --sh-degree-interval 1000 \
#     --ssim-weight 0.2 \
#     --refine-every 100 \
#     --warmup-length 500 \
#     --densify-grad-thresh 0.0001 \
#     --densify-size-thresh 0.005 \
#     --reset-alpha-every 30 \
#     --num-downscales 2 \
#     --resolution-schedule 3000 \
#     --save-every 5000 \
#     --val \
#     -o amtown02_30k_hq.ply \
#     2>&1 | tee train_30k_hq.log
