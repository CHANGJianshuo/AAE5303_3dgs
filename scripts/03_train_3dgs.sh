#!/bin/bash
# =============================================================
# AMtown02 3D Gaussian Splatting Training Script
# Framework: Original 3DGS (graphdeco-inria/gaussian-splatting)
# Commit: 2130164 (with patches applied, see docs/05_hyperparameters_guide.md)
# Hardware: NVIDIA A100 PCIe 40GB
# Data: 1,380 images (2448x2048), 343,815 initial points from LiDAR
# =============================================================

# Environment setup
export PATH=/root/miniconda3/bin:$PATH
export LD_LIBRARY_PATH=/root/miniconda3/lib/python3.12/site-packages/torch/lib:$LD_LIBRARY_PATH

GS_REPO=/root/autodl-tmp/gaussian-splatting
DATA_DIR=/root/autodl-tmp/AMtown02_colmap

cd ${GS_REPO}

# =============================================================
# Run 1: 10,000 iterations (quick convergence check)
# Expected: ~15 min on A100, Final Loss ~0.16
# =============================================================
python train.py \
    -s ${DATA_DIR} \
    -m /root/autodl-tmp/output_10k \
    --iterations 10000 \
    --sh_degree 3 \
    --resolution 4 \
    --save_iterations 5000 10000 \
    --test_iterations 5000 10000 \
    2>&1 | tee train_10k.log

# =============================================================
# Run 2: 30,000 iterations (full training)
# Expected: ~40 min on A100, Final Loss ~0.136
# =============================================================
python train.py \
    -s ${DATA_DIR} \
    -m /root/autodl-tmp/output_30k \
    --iterations 30000 \
    --sh_degree 3 \
    --resolution 4 \
    --save_iterations 10000 20000 30000 \
    --test_iterations 10000 20000 30000 \
    2>&1 | tee train_30k.log

# =============================================================
# Run 3: Maximum quality (-d 1 full resolution, requires CPU offload)
# Expected: ~6-7 hours on A100, Final Loss target <0.08
# Note: --data_device cpu is REQUIRED because 1380 full-res images
#       need ~77 GiB GPU memory, exceeding any single-card capacity.
# =============================================================
# python train.py \
#     -s ${DATA_DIR} \
#     -m /root/autodl-tmp/output_best \
#     --iterations 30000 \
#     --sh_degree 3 \
#     --resolution 1 \
#     --data_device cpu \
#     --densify_grad_threshold 0.0001 \
#     --densify_until_iter 20000 \
#     --save_iterations 10000 20000 30000 \
#     2>&1 | tee train_best.log
