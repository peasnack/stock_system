# A股投资决策系统 MVP

## 环境

Ubuntu 24.04，Python 3.11+。

```bash
sudo apt update
sudo apt install -y python3.12-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 单次运行

```bash
python main.py --once
```

## 启动每日定时任务

每天 14:50 执行分析并模拟微信推送：

```bash
python main.py
```

启动后如需立即执行一次再进入定时：

```bash
python main.py --run-now
```

## 输出格式

系统统一输出：

- `[市场状态]`
- `[指数数据]`
- `[个股数据]`
- `[风险状态]`
- `[交易建议]`
- `[理由]`

## 说明

数据源使用 AkShare：

- `stock_zh_a_spot_em`
- `stock_zh_index_spot_em`

如果 AkShare 获取失败或关键字段缺失，系统返回 `DATA_ERROR`，不会伪造行情数据。
