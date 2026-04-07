# AMtown02 UAVScenes 数据详解与 3DGS 输入验证

> 基于从 UAVScenes 下载的 `interval5_AMtown02` 实际数据分析

## 数据总览

```
interval5_AMtown02/ (2.2 GB)
├── sampleinfos_interpolated.json    # 位姿数据（T4x4 + P3x3），6,899 条
├── interval5_CAM/                   # 1,380 张 JPG 图片 (1.20 GB)
├── interval5_LIDAR/                 # 1,380 个 LiDAR txt (每帧~25,000点)
├── posest_viz.png                   # 位姿可视化图
├── rtk_positions_raw.csv            # RTK 原始位置
└── rtk_positions_raw_viz.png        # RTK 轨迹可视化图
```

---

## 一、图像数据 (`interval5_CAM/`)

| 属性 | 值 |
|------|-----|
| 数量 | **1,380 张** |
| 分辨率 | **2448 x 2048** |
| 单张大小 | 782 KB ~ 1,130 KB |
| 总大小 | **1.20 GB** |
| 来源 | Hikvision 相机，挂载在 DJI 无人机云台上 |
| 采样 | 原始 7,499 帧每 5 帧取 1 帧 |

---

## 二、LiDAR 数据 (`interval5_LIDAR/`)

| 属性 | 值 |
|------|-----|
| 数量 | **1,380 个 txt 文件** |
| 格式 | 每行 `x y z`（纯文本，空格分隔） |
| 每帧点数 | ~25,000 个 |
| 总点数 | **~3,450 万** |
| 文件命名 | `image<图片时间戳>_lidar<LiDAR时间戳>.txt` |
| 图像-LiDAR 时间差 | ~16 ms（近似同步） |

LiDAR 坐标已经转到了**世界坐标系**（和 T4x4 同一坐标系），可以直接合并。

### LiDAR 数据示例

```
40.251999 12.596000 10.090000
37.813000 11.877000 10.185000
42.505001 13.351000 11.449000
```

---

## 三、位姿数据 (`sampleinfos_interpolated.json`)

| 属性 | 值 |
|------|-----|
| JSON 总条目 | 6,899（对应 interval1 全量帧） |
| 与图片匹配的 | **1,380 条**（interval5 采样后） |

### 每条记录包含

| 字段 | 含义 | 示例值 |
|------|------|--------|
| `T4x4` | **Camera-to-World 变换矩阵** | 4x4 矩阵，含旋转 R 和平移 t |
| `P3x3` | **相机内参矩阵** | fx=1469.49, fy=1469.49, cx=1174.00, cy=1049.91 |
| `K1,K2,K3,P1,P2` | 畸变系数 | 全为 0（已去畸变或忽略） |
| `Width, Height` | 图像尺寸 | 2448 x 2048 |
| `OriginalImageName` | 对应图片文件名 | 时间戳.jpg |

### T4x4 矩阵示例（第一张图）

```
[  0.6514  -0.7576   0.0410  -431.8933 ]
[ -0.7578  -0.6523  -0.0140   -57.6733 ]
[  0.0373  -0.0219  -0.9991   -35.7546 ]
[  0.0000   0.0000   0.0000     1.0000 ]
```

- `det(R) = 1.000000`：合法旋转矩阵
- T4x4 是 **camera-to-world** 变换（相机到世界坐标系）
- 坐标系 Z 轴朝下，相机视线方向 Z 分量 ≈ +0.99
- 确认是**正射俯视（nadir）**拍摄

### 关于 T4x4 的来源

`sampleinfos_interpolated.json` 中的 T4x4 是 UAVScenes 数据集**已经融合好的最终相机位姿**，包含了：
- GPS/INS 硬件测量的无人机位置
- IMU 融合的机体姿态
- 云台角度
- LiDAR-Camera 外参标定

用户无需自己从 GPS+attitude+gimbal 拼接，数据集已经全部处理完毕。

---

## 四、空间覆盖分析

| 属性 | 值 |
|------|-----|
| X 范围 | -526.4 ~ 337.9 m（跨度 **864 m**） |
| Y 范围 | -67.2 ~ 518.7 m（跨度 **586 m**） |
| Z 范围 | -57.5 ~ 1.9 m（高度跨度 **59 m**） |
| 覆盖面积 | **864m x 586m ≈ 0.51 km²** |
| 飞行高度 | ~60-80 m AGL |
| 单张地面覆盖 | **133m x 111m**（在 80m 高度） |
| 相邻图片间距 | 平均 **3.5 m** |
| 前向重叠率 | **~97%** |

---

## 五、LiDAR 点云处理链路

baseline 对 LiDAR 做了两次采样：

```
1,380 个 LiDAR txt 文件
    共 ~3,450 万点
            |
            | merge_lidar_to_ply.py
            | sample_rate = 10（每10个取1个）
            v
    cloud_merged.ply
    ~345 万点，~49 MB
            |
            | convert_amtown02_to_colmap.py
            | load_ply_points() 再 sample_rate = 10
            v
    points3D.bin
    ~34.5 万点
            |
            v
    OpenSplat 读取 -> 初始化 ~34.5 万个高斯原语
```

LiDAR 坐标和 T4x4 在同一世界坐标系下，所以可以直接写入 points3D.bin，不需要额外坐标变换。

---

## 六、相机标定参数对比

### sampleinfos_interpolated.json 中的参数

```
fx = 1469.49, fy = 1469.49
cx = 1174.00, cy = 1049.91
K1 = K2 = K3 = P1 = P2 = 0（无畸变）
```

### AMtown.yaml 中的参数（来自 UAVScenes calibration_results.py）

```
fx = 1453.72, fy = 1453.28
cx = 1172.18, cy = 1041.78
K1 = -0.1210, K2 = 0.1113, P1 = 0.0016, P2 = 0.00013, K3 = -0.062353
```

### 差异说明

| 参数 | JSON | YAML | 说明 |
|------|------|------|------|
| fx | 1469.49 | 1453.72 | JSON 可能是优化后的值 |
| 畸变 | 全为 0 | 有值 | JSON 的图片可能已经去畸变 |

baseline 使用的是 JSON 中的参数（无畸变版本）。

---

## 七、是否满足 3DGS 输入要求

3DGS（OpenSplat）需要 COLMAP 格式的输入，包含三样东西：

| 需要 | AMtown02 是否具备 | 状态 |
|------|-------------------|------|
| **多视角图片** | 1,380 张 2448x2048 | 满足 |
| **相机位姿（外参）** | T4x4 camera-to-world | 满足（需用脚本转 COLMAP 格式） |
| **相机内参** | P3x3 fx/fy/cx/cy | 满足（需用脚本转 COLMAP 格式） |
| **初始 3D 点云** | LiDAR ~3,450 万点 | 满足（需合并+采样转 COLMAP 格式） |

**结论：完全满足 3DGS 输入要求。**

### 数据质量评估

| 维度 | 评价 | 说明 |
|------|------|------|
| 图片数量 | 优秀 | 1,380 张远超 3DGS 常见的几十~几百张 |
| 重叠率 | 极高 (97%) | 保证充分的多视角约束 |
| 位姿精度 | 高 | GPS/INS 硬件测量 + 插值，比纯 COLMAP 估计通常更准 |
| 点云密度 | 充足 | 3,450 万点，采样后仍有 34 万，足够初始化高斯 |
| 视角多样性 | 一般 | 几乎全是正射（朝下），缺少斜视角度，建筑侧面重建质量可能较差 |
| 分辨率 | 高 | 2448x2048，A100 40GB 可以不降采样直接训练 |

### 数据到 3DGS 的转换流程

```bash
# Step 1: 合并 LiDAR 点云
python3 baseline/scripts/merge_lidar_to_ply.py
# 输入: 1,380 个 txt -> 输出: cloud_merged.ply (345万点)

# Step 2: 转 COLMAP 格式
python3 baseline/scripts/convert_amtown02_to_colmap.py
# 输入: JSON + images + PLY -> 输出: AMtown02_colmap/

# Step 3: OpenSplat 训练
./opensplat /path/to/AMtown02_colmap -n 30000 -o output.ply
```
