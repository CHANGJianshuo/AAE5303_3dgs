# 完整项目运行流程

## 总览

```
原始照片 + LiDAR/位姿
        |
  merge_lidar_to_ply.py          <- 合并点云
  convert_amtown02_to_colmap.py  <- 转 COLMAP 格式
        |
  COLMAP 格式目录
  (images/ + sparse/0/*.bin)
        |
  OpenSplat 训练                 <- 核心步骤
  ./opensplat <colmap_dir> -n 30000 -o output.ply
        |
  output.ply（高斯模型）
        |
  analyze_training.py            <- 分析 loss
  evaluate_baseline.py           <- 评估质量
```

---

## 第一步：准备原始数据

### 方案 1：从 ROS Bag 提取（本项目实际情况）

输入：`AMtown02.bag`（17GB ROS bag）

```bash
python3 extract_bag.py
```

提取结果：
```
AMtown02_extracted/
├── images/                7,499 张 JPG (6.69 GB)
├── lidar/                 7,498 帧 LiDAR bin (9.55 GB)
├── image_timestamps.json
├── lidar_timestamps.json
├── attitudes.json         74,992 条姿态（四元数）
├── gps_positions.json     37,496 条 GPS
├── local_positions.json   37,496 条本地坐标
└── gimbal_angles.json     37,496 条云台角度
```

### 方案 2：直接使用 UAVScenes 已处理数据（baseline 做法）

从 UAVScenes 数据集（https://github.com/sijieaaa/UAVScenes）下载 AMtown02 序列：

```
interval5_AMtown02/
├── sampleinfos_interpolated.json    # 相机位姿 JSON（含 P3x3 内参、T4x4 外参）
├── interval5_CAM/                    # 1,380 张 JPG 照片（每5帧采样）
└── interval5_LIDAR/                  # 1,380 个 LiDAR txt 点云文件
```

### 方案 3：HKisland 数据集（课程提供，已处理好 COLMAP）

```
HKisland_colmap/
├── images/                           # 534 张 JPG 照片
└── sparse/0/
    ├── cameras.bin
    ├── images.bin
    └── points3D.bin
```

如果有这个数据，可以**直接跳到第三步**。

---

## 第二步：数据预处理（将原始数据转为 COLMAP 格式）

### 2a. 合并 LiDAR 点云

```bash
python3 baseline/scripts/merge_lidar_to_ply.py
```

| 项目 | 值 |
|------|-----|
| 输入 | 1,380 个 LiDAR txt 文件（共 34M 个点） |
| 处理 | 每 10 个点取 1 个（`sample_rate=10`） |
| 输出 | `cloud_merged.ply`（340 万点，49 MB） |
| 颜色 | LiDAR 无颜色信息，统一填灰色 `(128, 128, 128)` |

脚本内部逻辑：
1. 遍历所有 LiDAR txt 文件
2. 每行读取 xyz 坐标
3. 按采样率抽取
4. 写入 PLY 二进制格式（float xyz + uchar rgb）

### 2b. 转换为 COLMAP 格式

```bash
python3 baseline/scripts/convert_amtown02_to_colmap.py
```

| 项目 | 值 |
|------|-----|
| 输入 | JSON 位姿 + JPG 图片 + PLY 点云 |
| 输出 | `AMtown02_colmap/`（COLMAP 标准格式） |

脚本做了三件事：

**1) 生成 `cameras.bin`（相机内参）**
- 从 JSON 的 `P3x3` 矩阵提取 `fx, fy, cx, cy`
- 读取图片获取分辨率 `2448 x 2048`
- 相机模型：OPENCV（model_id=4）
- 参数：`fx=1469.49, fy=1469.49, cx=1174.00, cy=1049.91, k1=0, k2=0`

**2) 生成 `images.bin`（相机外参/位姿）**
- 从 JSON 的 `T4x4` 矩阵提取旋转矩阵 R 和平移 t
- 做求逆：`R_inv = R.T`, `t_inv = -R.T @ t`（转为 COLMAP 的 camera-to-world 约定）
- 旋转矩阵转四元数 `(qw, qx, qy, qz)`

**3) 生成 `points3D.bin`（3D 点云）**
- 从 PLY 再采样 1/10：340 万 -> **34 万点**
- 颜色填 `(128, 128, 128)` 灰色
- 每个点的 error 设为 1.0，track 为空

转换后的目录结构：
```
AMtown02_colmap/
├── images/            # 1,380 张照片（从原始目录复制）
└── sparse/0/
    ├── cameras.bin    # 1 个相机，OPENCV 模型
    ├── images.bin     # 1,380 张图的位姿
    └── points3D.bin   # 343,815 个 3D 点
```

---

## 第三步：OpenSplat 训练（核心）

### 3a. 编译 OpenSplat

```bash
git clone https://github.com/pierotofy/OpenSplat
cd OpenSplat
mkdir build && cd build
cmake -DCMAKE_PREFIX_PATH=/path/to/libtorch/ ..
make -j$(nproc)
```

A100 编译建议：
```bash
cmake -DCMAKE_PREFIX_PATH=/path/to/libtorch/ \
      -DGPU_RUNTIME=CUDA \
      -DCMAKE_BUILD_TYPE=Release \
      ..
```

### 3b. 运行训练

**CPU 训练（baseline 做法，仅用于验证）：**
```bash
./opensplat /path/to/AMtown02_colmap \
    --cpu \
    -n 300 \
    -d 4 \
    -o amtown02_output_300.ply
```

**A100 GPU 训练（推荐）：**
```bash
./opensplat /path/to/AMtown02_colmap \
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
    -o amtown02_30k.ply
```

| 项目 | 值 |
|------|-----|
| 输入 | COLMAP 格式目录（images/ + sparse/0/*.bin） |
| 输出 | PLY 文件（包含所有高斯原语的位置、协方差、颜色、透明度） |

### 3DGS 训练过程

```
COLMAP 输入 (SfM + Images)
        |
  初始化高斯（每个 3D 点 -> 一个高斯）
        |
  循环 30,000 次:
  |  1. 随机选一张图
  |  2. 用当前高斯渲染该视角的图像（前向传播）
  |  3. 和真实照片比较，计算 Loss = 0.8*L1 + 0.2*(1-SSIM)
  |  4. 反向传播，更新高斯参数（位置、大小、颜色、透明度）
  |  5. 每 100 步做密度控制：
  |     - 分裂：梯度大且尺寸大的高斯 -> 拆成两个更小的
  |     - 克隆：梯度大且尺寸小的高斯 -> 复制一份到附近
  |     - 修剪：透明度太低或尺寸太大的高斯 -> 删除
        |
  输出 PLY（百万~千万级高斯原语）
```

---

## 第四步：训练分析（可选）

```bash
python3 scripts/analyze_training.py
```

| 项目 | 值 |
|------|-----|
| 输入 | 训练日志 txt（OpenSplat 的 stdout 输出） |
| 输出 | 4 张可视化图表 |

生成的图表：
- `training_loss_curve.png` - Loss 随迭代步数的变化曲线 + 移动平均
- `loss_distribution.png` - Loss 值的直方图 + 箱线图
- `convergence_analysis.png` - 对数 loss、梯度分析、滚动统计、阶段对比
- `summary_dashboard.png` - 综合 Dashboard（曲线 + 分布 + 关键指标卡片 + 配置表）

---

## 第五步：质量评估（可选）

```bash
python3 baseline/evaluate_baseline.py \
    --rendered <渲染图目录> \
    --gt <真实图目录> \
    --output baseline_results.json
```

| 项目 | 值 |
|------|-----|
| 输入 | 模型渲染的测试图片 + 对应的真实图片 |
| 输出 | PSNR、SSIM、LPIPS 指标 |

评估指标说明：

| 指标 | 含义 | 越高/低越好 | 优秀范围 |
|------|------|-------------|----------|
| **PSNR** | 峰值信噪比（dB） | 越高越好 | > 25 dB |
| **SSIM** | 结构相似度 (0-1) | 越高越好 | > 0.85 |
| **LPIPS** | 感知距离 (0-1) | 越低越好 | < 0.15 |

---

## 两条 Pipeline 的对比

### HKisland Pipeline（传统 3DGS 流程）

```
534 张 UAV 照片
      |
  COLMAP SfM（项目之前已跑好）
  |-- 特征提取（SIFT）
  |-- 特征匹配
  |-- 增量式 SfM -> 估计相机位姿
  |-- 三角化 -> 稀疏点云（144 万点）
      |
  HKisland_colmap/（现成的 COLMAP 输出）
      |
  OpenSplat 训练
      |
  output.ply
```

### AMtown02 Pipeline（LiDAR + 已知位姿）

```
UAVScenes 数据集 / ROS Bag 提取
|-- 1,380 张照片
|-- LiDAR 点云
|-- 已知位姿（JSON / GPS+IMU+Gimbal）
      |
  merge_lidar_to_ply.py     <- 合并 LiDAR
  convert_to_colmap.py      <- 伪造 COLMAP 格式
      |
  AMtown02_colmap/（格式和 HKisland 完全一样）
      |
  OpenSplat 训练（完全相同的命令）
      |
  output.ply
```

### 核心区别

| 方面 | HKisland | AMtown02 |
|------|----------|----------|
| **位姿来源** | COLMAP 从照片估计 | 数据集自带（GPS/INS 硬件测量） |
| **点云来源** | COLMAP 三角化（视觉特征点） | LiDAR 扫描 |
| **需要跑 COLMAP** | 是（已经跑好） | 不需要 |
| **需要预处理脚本** | 不需要 | 需要合并点云 + 格式转换 |
| **点云有颜色** | 有（COLMAP 从照片提取） | 没有（LiDAR 无颜色，填灰色） |
| **位姿精度** | 取决于 COLMAP 匹配质量 | 通常更准（硬件测量） |
| **点云密度** | 稀疏（仅特征点位置） | 密集（LiDAR 全覆盖），但采样后变稀 |

**最终都生成相同格式的 COLMAP 目录**，OpenSplat 的输入和训练过程完全一致。

---

## 环境依赖

### Python 依赖

```
# 数据提取
rosbags          # 解析 ROS bag 文件
Pillow           # 图像处理

# 训练分析
numpy
matplotlib

# 评估（可选）
scikit-image     # PSNR, SSIM
torch            # PyTorch
lpips            # 感知距离
opencv-python    # 图像 I/O
```

### 系统依赖

```
# OpenSplat 编译
cmake >= 3.16
g++ (C++17 support)
libtorch (PyTorch C++ frontend)
CUDA toolkit (for GPU training)
```

### 建议使用虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install rosbags Pillow numpy matplotlib
# 评估时再安装
pip install scikit-image torch lpips opencv-python
```
