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

启用 AI 决策模块但只打印、不推送：

```bash
python main.py --mode late --ai --dry-run
```

## 常用执行命令

在当前 Ubuntu 桌面已登录微信时，手动执行完整分析并推送到文件传输助手：

```bash
cd /home/hlw/repos/personal/stock_system

export NOTIFY_ENABLED=true
export NOTIFY_CHANNEL=linux_wechat_gui
export LINUX_WECHAT_TARGET="文件传输助手"

.venv/bin/python main.py --once --mode late --ai --notify
```

启动每日 14:50 自动分析并推送到文件传输助手：

```bash
cd /home/hlw/repos/personal/stock_system

export NOTIFY_ENABLED=true
export NOTIFY_CHANNEL=linux_wechat_gui
export LINUX_WECHAT_TARGET="文件传输助手"

.venv/bin/python main.py --mode late --ai
```

执行前可检查桌面自动化工具是否可用：

```bash
command -v xdotool
command -v xclip
```

## 配置

默认配置在 `config.py`。如需调整股票池、指数、阈值、定时任务或通知参数，可复制示例配置：

```bash
cp app_config.example.json app_config.json
```

`app_config.json` 是本地配置文件，默认不会提交到 Git。

如需让建议结合持仓成本和账户仓位，在 `app_config.json` 中填写本地持仓：

```json
{
  "portfolio": {
    "cash": 0,
    "positions": {
      "601138": {
        "quantity": 100,
        "cost": 50.0
      }
    }
  }
}
```

系统不会连接真实券商账户，持仓成本和账户仓位只从本地配置读取。

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

如果 14:50 没有收到微信，优先检查：

- 定时进程是否仍在运行，日志在 `logs/stock_system.log`
- `NOTIFY_ENABLED=true`
- `NOTIFY_CHANNEL=linux_wechat_gui` 或 `webhook`
- Linux 微信方式需要 `xdotool`、`xclip`，且微信已登录、窗口可见、屏幕未锁定
- 手动执行 `python main.py --once --mode late --notify` 验证通知链路

如需启用企业微信机器人 webhook，可设置：

```bash
export NOTIFY_ENABLED=true
export NOTIFY_CHANNEL=webhook
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
python main.py --once
```

## AI 决策模块 MVP2

AI 模块会先保存标准化上下文，再调用 OpenAI，最后由本地二次风控修正 AI 输出。缺少 `OPENAI_API_KEY`、SDK 未安装或 API 调用失败时，系统仍会输出并推送本地规则结果，结论标注 `AI_ERROR，按本地风控执行`。

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
python main.py --mode late --ai --dry-run
```

每次运行会保存：

- `data/context/YYYY-MM-DD_HHMM_market_context.json`
- `data/decision/YYYY-MM-DD_HHMM_ai_raw.json`
- `data/decision/YYYY-MM-DD_HHMM_decision_guarded.json`
- `data/reports/YYYY-MM-DD_HHMM_report.md`

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
- `stock_financial_abstract`
- `stock_news_em`
- `stock_research_report_em`
- `stock_hsgt_fund_flow_summary_em`
- `stock_hsgt_individual_em`
- `stock_lhb_stock_detail_date_em`
- `stock_lhb_stock_detail_em`
- `stock_individual_fund_flow`
- `stock_sector_fund_flow_rank`
- `stock_board_industry_name_em`
- `stock_zh_a_hist`

指数数据优先使用新浪源，目标指数缺失或接口失败时回退到东方财富源。交易日优先从行情数据解析，解析不到时使用 AkShare 交易日历。

投资建议前会额外抓取财报、新闻、研报、北向资金、龙虎榜、资金流向、行业板块行情、个股历史 K 线，并结合本地配置中的持仓成本和账户仓位。

如果 AkShare 获取失败或关键字段缺失，系统返回 `DATA_ERROR`，不会伪造行情数据。

## 验证

```bash
python3 -m compileall main.py config.py core data notify scheduler tests
python3 -m unittest discover -s tests
python main.py --mode late --ai --dry-run
```
