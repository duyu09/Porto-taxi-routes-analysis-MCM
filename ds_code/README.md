# 面向智慧城市的出租车出行行为建模与路径优化研究

本目录是面向智慧城市的出租车出行行为建模与路径优化研究的完整 Python 代码包，围绕 Porto Taxi Trajectory 数据构建：

1. 出租车行为模式分析：数据清洗、轨迹特征工程、XGBoost 分类、SHAP 可解释分析、OD 矩阵与热点流向分析。
2. 基于行为模式的路径规划：OSM 路网构建、轨迹点投影/近似 map matching、动态边权重生成、乘客视角与司机视角路径规划、基线与消融实验。

> 设计原则：CSV 默认无表头。若 Porto 原始文件带表头，程序会自动识别并兼容；也可以在 `config/default.yaml` 中显式设置 `data.has_header: true`。

## 目录结构

```text
./
├── config/default.yaml              # 全局配置
├── data/README.md                   # 数据放置说明
├── scripts/
│   ├── make_demo_data.py             # 生成小型演示数据
│   ├── run_all.py                    # 一键流水线
│   └── run_smoke_test.py             # 快速冒烟测试
├── src/smart_taxi/
│   ├── cli.py                        # 命令行入口
│   ├── data/                         # 读取、清洗、特征构建
│   ├── models/                       # 模型训练、评估、SHAP
│   ├── od/                           # OD 分析
│   ├── routing/                      # OSM 路网、map matching、动态 cost、路径规划
│   ├── experiments/                  # 对比实验与消融实验
│   ├── visualization/                # 图表工具
│   └── utils/                        # 配置、日志、地理工具
└── tests/                            # 基础单元测试
```

## 环境安装

建议使用 Python 3.10+。

```bash
cd smart_taxi_porto
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

OSMnx/GeoPandas 在部分 Windows 环境安装较慢，推荐使用 conda：

```bash
conda create -n taxi-smart python=3.11 -y
conda activate taxi-smart
conda install -c conda-forge osmnx geopandas shapely pyproj rtree -y
pip install -r requirements.txt
pip install -e .
```

## 数据准备

将 Porto 训练集放在：

```text
data/raw/train.csv
```

默认列顺序为：

```text
TRIP_ID,CALL_TYPE,ORIGIN_CALL,ORIGIN_STAND,TAXI_ID,TIMESTAMP,DAY_TYPE,MISSING_DATA,POLYLINE
```

如果你的 CSV 没有表头，不需要额外操作。如果有表头，程序会自动兼容，也可以改配置：

```yaml
data:
  has_header: true
```

## 快速运行 DEMO

没有真实数据时，可先生成演示数据并跑通全流程中的轻量部分：

```bash
python scripts/make_demo_data.py --out data/raw/demo_no_header.csv --n 300
python -m smart_taxi.cli build-features --input data/raw/demo_no_header.csv --output outputs/features/demo_features.csv --config config/default.yaml
python -m smart_taxi.cli train-model --features outputs/features/demo_features.csv --output-dir outputs/models/demo --config config/default.yaml
python -m smart_taxi.cli od-analysis --features outputs/features/demo_features.csv --output-dir outputs/od/demo --config config/default.yaml
```

## 真实数据推荐流程

### 1. 构建特征表

```bash
python -m smart_taxi.cli build-features \
  --input data/raw/train.csv \
  --output outputs/features/porto_features.parquet \
  --config config/default.yaml
```

### 2. 训练行为分类模型

```bash
python -m smart_taxi.cli train-model \
  --features outputs/features/porto_features.parquet \
  --output-dir outputs/models/xgb_call_type \
  --config config/default.yaml
```

### 3. SHAP 解释

```bash
python -m smart_taxi.cli shap-analysis \
  --features outputs/features/porto_features.parquet \
  --model-dir outputs/models/xgb_call_type \
  --output-dir outputs/shap/xgb_call_type \
  --config config/default.yaml
```

### 4. OD 分析

```bash
python -m smart_taxi.cli od-analysis \
  --features outputs/features/porto_features.parquet \
  --output-dir outputs/od/porto \
  --config config/default.yaml
```

### 5. 构建 OSM 路网

```bash
python -m smart_taxi.cli build-network \
  --place "Porto, Portugal" \
  --output outputs/network/porto_drive.graphml \
  --config config/default.yaml
```

或者可以使用边界框：

```bash
python -m smart_taxi.cli build-network \
  --bbox 41.05 41.25 -8.75 -8.45 \
  --output outputs/network/porto_drive.graphml \
  --config config/default.yaml
```

### 6. 生成边统计与动态权重

```bash
python -m smart_taxi.cli build-edge-stats \
  --features outputs/features/porto_features.parquet \
  --network outputs/network/porto_drive.graphml \
  --output outputs/network/edge_stats.csv \
  --config config/default.yaml
```

### 7. 路径规划

```bash
python -m smart_taxi.cli plan-route \
  --network outputs/network/porto_drive.graphml \
  --edge-stats outputs/network/edge_stats.csv \
  --origin-lat 41.14961 --origin-lon -8.61099 \
  --dest-lat 41.16214 --dest-lon -8.62195 \
  --time "2014-01-15 08:30:00" \
  --profile passenger \
  --output outputs/routes/passenger_route.geojson \
  --config config/default.yaml
```

司机视角：

```bash
python -m smart_taxi.cli plan-route \
  --network outputs/network/porto_drive.graphml \
  --edge-stats outputs/network/edge_stats.csv \
  --origin-lat 41.14961 --origin-lon -8.61099 \
  --dest-lat 41.16214 --dest-lon -8.62195 \
  --time "2014-01-15 08:30:00" \
  --profile driver \
  --output outputs/routes/driver_route.geojson \
  --config config/default.yaml
```

### 8. 一键流水线

```bash
python scripts/run_all.py \
  --input data/raw/train.csv \
  --network-place "Porto, Portugal" \
  --config config/default.yaml \
  --output-root outputs/full_run
```

## 输出物说明

- `features/*.csv|parquet`：订单级特征表。
- `models/*/model.joblib`：包含预处理器与模型的 sklearn pipeline。
- `models/*/metrics.json`：Accuracy、Macro-F1、Precision、Recall、AUC 等。
- `shap/*/shap_feature_importance.csv`：平均绝对 SHAP 重要性。
- `od/*/od_matrix.csv`：不同时间段 OD 流量矩阵。
- `network/*.graphml`：OSM 路网。
- `network/edge_stats.csv`：边级历史速度、拥堵、上客概率等统计结果。
- `routes/*.geojson`：规划路径，可直接用 QGIS、Kepler.gl 或 GeoPandas 查看。

## 建模口径

- 行程时长：`(轨迹点数 - 1) * 15` 秒。
- Porto `POLYLINE` 中坐标顺序为 `[longitude, latitude]`。
- 默认目标标签为 `CALL_TYPE`，可在配置中切换到规则型模式标签。
- 复合边成本采用：基础代价 × 环境放大项。
- 司机视角使用非负化的最小化成本近似最大化收益，以保证 Dijkstra/A* 可用。

