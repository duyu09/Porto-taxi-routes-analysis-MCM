# 数据目录

请将原始 Porto 数据放到：

```text
data/raw/train.csv
```

本项目默认 CSV 无表头。若使用 Kaggle/UCI 原始版本，通常自带表头，程序会自动识别第一行列名并兼容。

推荐目录：

```text
data/
├── raw/          # 原始数据
├── interim/      # 清洗中间结果
└── processed/    # 特征表等处理结果
```
