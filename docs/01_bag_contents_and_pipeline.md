# AMtown02 ROS Bag 数据内容与 3DGS Pipeline

## Bag 文件概览

| 属性 | 值 |
|------|-----|
| 文件 | AMtown02.bag |
| 大小 | 17 GB |
| 格式 | ROS BAG V2.0 |
| 时长 | 749.8 秒（12.5 分钟） |
| 消息总数 | 1,200,680 |
| 连接数 | 32 |

---

## Topic 列表与说明

### 关键传感器数据

| Topic | 类型 | 数量 | 说明 |
|-------|------|------|------|
| `/left_camera/image/compressed` | `sensor_msgs/CompressedImage` | 7,499 | 左相机压缩图像 |
| `/livox/lidar` | `livox_ros_driver/CustomMsg` | 7,498 | Livox LiDAR 点云 |
| `/livox/imu` | `sensor_msgs/Imu` | 156,060 | Livox IMU 数据 |

### DJI 飞控数据

| Topic | 类型 | 数量 | 频率 | 说明 |
|-------|------|------|------|------|
| `/dji_osdk_ros/attitude` | `QuaternionStamped` | 74,992 | 100 Hz | 机体姿态（四元数） |
| `/dji_osdk_ros/imu` | `Imu` | 299,964 | 400 Hz | IMU 加速度+角速度 |
| `/dji_osdk_ros/gps_position` | `NavSatFix` | 37,496 | 50 Hz | GPS 位置 |
| `/dji_osdk_ros/local_position` | `PointStamped` | 37,496 | 50 Hz | 本地/ECEF 坐标 |
| `/dji_osdk_ros/gimbal_angle` | `Vector3Stamped` | 37,496 | 50 Hz | 云台角度 |
| `/dji_osdk_ros/velocity` | `Vector3Stamped` | 37,496 | 50 Hz | 飞行速度 |
| `/dji_osdk_ros/height_above_takeoff` | `Float32` | 37,496 | 50 Hz | 离地高度 |
| `/dji_osdk_ros/angular_velocity_fused` | `Vector3Stamped` | 74,991 | 100 Hz | 融合角速度 |
| `/dji_osdk_ros/acceleration_ground_fused` | `Vector3Stamped` | 74,991 | 100 Hz | 融合加速度 |

### RTK 高精度定位

| Topic | 类型 | 数量 | 频率 | 说明 |
|-------|------|------|------|------|
| `/dji_osdk_ros/rtk_position` | `NavSatFix` | 3,750 | 5 Hz | RTK 位置 |
| `/dji_osdk_ros/rtk_velocity` | `Vector3Stamped` | 3,750 | 5 Hz | RTK 速度 |
| `/dji_osdk_ros/rtk_yaw` | `Int16` | 3,750 | 5 Hz | RTK 偏航角 |

### 状态与控制

| Topic | 类型 | 数量 | 说明 |
|-------|------|------|------|
| `/dji_osdk_ros/flight_status` | `UInt8` | 37,496 | 飞行状态 |
| `/dji_osdk_ros/display_mode` | `UInt8` | 37,496 | 显示模式 |
| `/dji_osdk_ros/gps_health` | `UInt8` | 37,496 | GPS 信号质量 |
| `/dji_osdk_ros/battery_state` | `BatteryState` | 3,750 | 电池状态 |
| `/dji_osdk_ros/rc` | `Joy` | 37,496 | 遥控器输入 |
| `/dji_osdk_ros/rc_connection_status` | `UInt8` | 37,496 | 遥控器连接状态 |
| `/dji_osdk_ros/flight_anomaly` | `FlightAnomaly` | 37,496 | 飞行异常 |

### 时间同步

| Topic | 类型 | 数量 | 说明 |
|-------|------|------|------|
| `/dji_osdk_ros/time_sync_fc_time_utc` | `FCTimeInUTC` | 750 | 飞控 UTC 时间 |
| `/dji_osdk_ros/time_sync_pps_source` | `String` | 750 | PPS 源 |
| `/dji_osdk_ros/time_sync_nmea_msg` | `Sentence` | 18,733 | NMEA 消息 |
| `/dji_osdk_ros/time_sync_gps_utc` | `GPSUTC` | 750 | GPS UTC 时间 |

---

## 从 Bag 到 3DGS 的完整 Pipeline

```
AMtown02.bag (17GB ROS bag)
        |
        | 提取 (extract_bag.py)
        v
  +---------------------------------------------+
  |  7,499 张照片 (compressed image)             |
  |  7,498 帧 LiDAR 点云 (livox)                |
  |  GPS/RTK 位置 + IMU 姿态 + 云台角度          |
  +---------------------------------------------+
        |
        | 预处理
        v
  +---------------------------------------------+
  |  方案A: 用 GPS/IMU/gimbal 算相机位姿         |
  |         + 合并 LiDAR 点云                    |
  |         -> 转 COLMAP 格式（仓库已有脚本）     |
  |                                              |
  |  方案B: 只提取照片 -> 跑 COLMAP SfM          |
  |         -> 直接得到 COLMAP 格式              |
  +---------------------------------------------+
        |
        v
  COLMAP 格式目录
  (images/ + sparse/0/*.bin)
        |
        | OpenSplat 训练（A100 GPU）
        v
  output.ply（高斯模型）
        |
        v
  analyze_training.py  <- 分析 loss
  evaluate_baseline.py <- 评估质量 (PSNR/SSIM/LPIPS)
```

---

## Loss 指标含义

仓库 baseline（AMtown02, CPU 300 步）的结果：

| 指标 | 值 | 含义 |
|------|-----|------|
| **Initial Loss** | 0.2164 | 第 1 步的 loss，高斯还没优化，渲染图和真实照片差距大 |
| **Final Loss** | 0.0888 | 最后一步的 loss，越低越好 |
| **Minimum Loss** | 0.0454 | 训练过程中某一步达到的最低 loss（某些视角特别好） |
| **Maximum Loss** | 0.2147 | 训练中最差的一步（某些难视角） |
| **Mean Loss** | 0.1334 | 所有步的平均 loss |
| **Std Deviation** | 0.0346 | loss 波动幅度，越小越稳定 |
| **Loss Reduction** | 58.9% | (初始-最终)/初始，下降了多少 |

### Loss 计算公式

```
Loss = (1 - lambda_SSIM) * L1 + lambda_SSIM * (1 - SSIM)
     = 0.8 * L1 + 0.2 * (1 - SSIM)
```

- **L1**：渲染图和真实图的逐像素绝对误差，衡量颜色/亮度还原度
- **SSIM**：结构相似度指数（考虑亮度、对比度、结构），衡量人眼感知质量
- **lambda_SSIM = 0.2**：SSIM 权重，默认 0.2

### 如何降低 Loss

1. **增加迭代次数**：baseline 只跑了 300 步（推荐 30,000），密度控制（分裂/克隆）根本没启动（warmup=500 > 训练步数 300）
2. **让密度控制生效**：迭代数 > warmup_length 后，高斯才会分裂/克隆增加细节
3. **不降采样**：用原始分辨率训练能捕获更多细节
4. **GPU 加速**：使训练更多步数成为可能

---

## A100 PCIe 40GB 上的超参数建议

### 推荐配置

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

### 参数详解

| 参数 | baseline 值 | A100 建议 | 理由 |
|------|-------------|-----------|------|
| `-n` 迭代数 | 300 | **30,000** | baseline 只跑了 1%，密度控制都没启动。30k 是标准值 |
| `-d` 降采样 | 4 | **1（不降采样）** | A100 40GB 显存足够用原始分辨率 2448x2048 |
| `--sh-degree` | 3 | **3** | 最高阶球谐，视角相关颜色更好，A100 内存无压力 |
| `--sh-degree-interval` | 1000 | **1000** | 每 1000 步提升一级 SH，渐进式学习颜色 |
| `--ssim-weight` | 0.2 | **0.2** | 默认值平衡了锐度和结构，UAV 场景适用 |
| `--refine-every` | 100 | **100** | 每 100 步做一次密度控制（分裂/克隆/修剪），默认值合理 |
| `--warmup-length` | 500 | **500** | 前 500 步只优化参数不做分裂/克隆，让高斯先稳定 |
| `--densify-grad-thresh` | 0.0002 | **0.0002** | 梯度阈值，越低则更多高斯被分裂，更精细但更慢 |
| `--densify-size-thresh` | 0.01 | **0.01** | 小于此阈值的高斯克隆，大于的分裂 |
| `--reset-alpha-every` | 30 | **30** | 每 30 次 refine 重置透明度，防止伪影 |
| `--resolution-schedule` | 3000 | **3000** | 前 3000 步用低分辨率，之后逐步提升到原始分辨率 |
| `--num-downscales` | 2 | **2** | 渐进式分辨率的阶段数 |
| `--save-every` | 无 | **5000** | 每 5000 步保存一个 checkpoint |
| `--val` | 无 | **启用** | 留出验证集评估实际 PSNR/SSIM |

### 预计训练效果对比

| 指标 | baseline (CPU 300步) | A100 预期 (30k步) |
|------|----------------------|-------------------|
| 训练时间 | 25 分钟 | **30-60 分钟**（~1500张）/ **2.5-5 小时**（全部7499张） |
| Final Loss | 0.0888 | **0.01-0.03** |
| Min Loss | 0.0454 | **< 0.01** |
| Loss Reduction | 58.9% | **> 95%** |
| PSNR | ~20-22 dB | **25-30 dB** |
| SSIM | ~0.75-0.80 | **0.85-0.92** |
| 高斯数量 | 833 万（不变） | **可能增长到 1000-2000 万** |
| 输出 PLY 大小 | 2.0 GB | **2-5 GB** |
| 显存占用 | N/A | **15-25 GB** |

### 不同策略对比

| 策略 | 命令差异 | 时间 | 质量 | 适用场景 |
|------|----------|------|------|----------|
| 快速测试 | `-n 7000 -d 2` | 5-10 min | 中等 | 先验证数据对不对 |
| 标准训练 | `-n 30000 -d 1` | 30-60 min | 高 | 正式提交 |
| 极致质量 | `-n 30000 -d 1 --densify-grad-thresh 0.0001` | 60-90 min | 最高 | 追求最佳效果 |

> 注：以上时间基于 ~1,500 张图片（每5帧采样）。若使用全部 7,499 张，时间约乘以 5。
