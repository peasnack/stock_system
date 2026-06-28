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

## 配置

默认配置在 `config.py`。如需调整股票池、指数、阈值、定时任务或通知参数，可复制示例配置：

```bash
cp app_config.example.json app_config.json
```

`app_config.json` 是本地配置文件，默认不会提交到 Git。

## 启动每日定时任务

默认每天 14:50 执行分析并模拟微信推送：

```bash
python main.py
```

启动后如需立即执行一次再进入定时：

```bash
python main.py --run-now
```

## 通知

系统默认不发送真实 webhook，只在终端模拟输出消息。

如需启用企业微信机器人 webhook，可设置：

```bash
export NOTIFY_ENABLED=true
export NOTIFY_CHANNEL=webhook
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
python main.py --once
```

如需通过 Ubuntu 本机微信发送给文件传输助手，可安装桌面自动化工具并设置：

```bash
sudo apt install -y xdotool xclip
export NOTIFY_ENABLED=true
export NOTIFY_CHANNEL=linux_wechat_gui
export LINUX_WECHAT_TARGET="文件传输助手"
python main.py --once
```

该方式依赖当前桌面会话中的微信窗口，适合个人提醒试用；运行时需要微信已登录、窗口可见、屏幕未锁定。若无法使用 sudo，可将 `xdotool` 和 `xclip` 放入用户 PATH，例如 `~/bin`。

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
- `stock_zh_index_spot_sina`
- `stock_zh_index_spot_em`
- `tool_trade_date_hist_sina`

指数数据优先使用新浪源，目标指数缺失或接口失败时回退到东方财富源。交易日优先从行情数据解析，解析不到时使用 AkShare 交易日历。

如果 AkShare 获取失败或关键字段缺失，系统返回 `DATA_ERROR`，不会伪造行情数据。

## 验证

```bash
python3 -m compileall main.py config.py core data notify scheduler tests
python3 -m unittest discover -s tests
python main.py --once
```
