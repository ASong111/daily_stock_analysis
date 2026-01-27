# 🚀 快速参考卡片

## 📦 一分钟快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
vim .env  # 配置至少一个AI API Key

# 3. 运行分析
python main.py 600519

# 4. 智能选股
python select_stocks.py --days 3 --top 10
```

---

## 🎯 核心命令速查

### 股票分析
```bash
# 分析单只股票
python main.py 600519

# 批量分析
python main.py 600519 000001 300750

# 不使用AI分析（仅技术面）
python main.py 600519 --no-ai

# 包含新闻搜索
python main.py 600519 --search-news
```

### 智能选股
```bash
# 基础选股（默认参数）
python select_stocks.py

# 自定义参数
python select_stocks.py \
  --days 3 \              # 近3日热门板块
  --top 10 \              # 返回10只股票
  --min-score 60 \        # 最低评分60
  --stocks-per-sector 1   # 每板块1只

# 降低标准（更多结果）
python select_stocks.py --min-score 50 --stocks-per-sector 2
```

### Web服务
```bash
# 启动Web服务器
python web/server.py

# 访问API
curl http://localhost:8080/health
curl http://localhost:8080/analysis?code=600519
```

### 机器人
```bash
# 钉钉机器人
python -m bot.platforms.dingtalk_stream

# 飞书机器人
python -m bot.platforms.feishu_stream

# Discord机器人
python -m bot.platforms.discord
```

---

## 📁 核心文件速查

| 文件 | 功能 | 何时使用 |
|------|------|----------|
| `main.py` | 股票分析主程序 | 分析个股 |
| `select_stocks.py` | 智能选股工具 | 寻找买点 |
| `src/stock_analyzer.py` | 技术分析器 | 理解技术指标 |
| `src/analyzer.py` | AI分析器 | 理解AI分析 |
| `data_provider/` | 数据源管理 | 添加数据源 |
| `bot/` | 机器人模块 | 配置机器人 |
| `.env` | 环境配置 | 配置API Key |

---

## 🔑 必需配置

### 最小配置（仅技术分析）
```env
# 无需配置，直接运行
python main.py 600519 --no-ai
```

### 推荐配置（AI分析）
```env
# 选择一个AI服务（推荐Gemini，免费额度大）
GEMINI_API_KEY=your_key_here

# 或者使用Claude
CLAUDE_API_KEY=your_key_here

# 或者使用OpenAI
OPENAI_API_KEY=your_key_here
```

### 完整配置（所有功能）
```env
# AI分析
GEMINI_API_KEY=xxx
CLAUDE_API_KEY=xxx
OPENAI_API_KEY=xxx

# 数据源（推荐配置Tushare）
TUSHARE_TOKEN=xxx

# 新闻搜索
BOCHA_API_KEY=xxx
TAVILY_API_KEY=xxx
SERPAPI_KEY=xxx

# 自选股列表
STOCK_LIST=600519,000001,300750
```

---

## 🎨 输出格式

### 技术分析输出
```
【技术分析】贵州茅台 (600519)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 综合评分: 85分 (强烈买入)
📈 趋势状态: 强势多头
📉 均线系统: 多头排列 (MA5>MA10>MA20>MA60)
📊 MACD: 零轴上金叉
📊 KDJ: 超买区间
💰 量能状态: 放量上涨
```

### 选股输出
```markdown
# 📈 精准选股结果

## 🎯 推荐股票

### 1. 贵州茅台（600519）
**综合评分：** 85分 | **信号：** 强烈买入 | **趋势：** 强势多头

#### 💡 买入理由
**技术面：** 强势多头排列，均线发散上行；MACD金叉
**板块逻辑：** 白酒板块资金持续流入
**基本面：** 大盘股（市值2.5万亿）；估值合理（PE 35）
**催化剂：** 年报预告业绩增长，机构持续增持
```

---

## 🔍 技术指标说明

### 趋势判断
- **强势多头**: MA5 > MA10 > MA20 > MA60，均线发散
- **多头排列**: MA5 > MA10 > MA20，趋势向上
- **空头排列**: MA5 < MA10 < MA20，趋势向下
- **震荡整理**: 均线粘合，方向不明

### 买入信号
- **强烈买入** (80-100分): 多头排列 + 金叉 + 放量
- **买入** (60-79分): 多头排列 + 回踩支撑
- **观望** (40-59分): 震荡整理
- **卖出** (<40分): 空头排列

### 乖离率
- **< -5%**: 超跌，可能反弹
- **-5% ~ 0%**: 回踩支撑，买点
- **0% ~ 5%**: 正常上涨
- **> 5%**: 超买，注意风险

---

## 🐛 常见问题速查

### 问题1: 数据获取失败
```bash
# 检查网络
ping www.baidu.com

# 检查日志
tail -f logs/stock_analysis.log

# 手动指定数据源
# 编辑 data_provider/__init__.py
```

### 问题2: AI分析失败
```bash
# 测试API连接
python -c "from src.analyzer import GeminiAnalyzer; print(GeminiAnalyzer().is_available())"

# 检查配置
cat .env | grep API_KEY

# 使用其他AI模型
# 在 .env 中配置其他API Key
```

### 问题3: 选股无结果
```bash
# 降低筛选标准
python select_stocks.py --min-score 50

# 增加每板块股票数
python select_stocks.py --stocks-per-sector 2

# 查看详细日志
python select_stocks.py 2>&1 | tee select.log
```

### 问题4: 机器人无响应
```bash
# 检查机器人配置
cat .env | grep -E "DINGTALK|FEISHU|DISCORD"

# 查看机器人日志
tail -f logs/bot.log

# 重启机器人
pkill -f "bot.platforms"
python -m bot.platforms.dingtalk_stream
```

---

## 📊 性能优化建议

### 1. 数据缓存
```python
# 在 data_provider/ 中添加缓存
import functools
from datetime import datetime, timedelta

@functools.lru_cache(maxsize=100)
def get_cached_data(code, date):
    # 缓存当日数据
    pass
```

### 2. 并发分析
```python
# 使用多线程批量分析
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(analyze_stock, stock_codes)
```

### 3. API限流
```python
# 添加请求间隔
import time

for stock in stocks:
    analyze(stock)
    time.sleep(1)  # 避免API限流
```

---

## 🎓 学习资源

### 技术分析基础
- 均线系统: [Investopedia - Moving Averages](https://www.investopedia.com/terms/m/movingaverage.asp)
- MACD指标: [MACD详解](https://www.investopedia.com/terms/m/macd.asp)
- KDJ指标: [KDJ使用指南](https://www.investopedia.com/terms/s/stochasticoscillator.asp)

### Python量化
- Pandas数据处理: [Pandas官方文档](https://pandas.pydata.org/)
- TA-Lib技术指标: [TA-Lib文档](https://mrjbq7.github.io/ta-lib/)

### AI应用
- Prompt工程: [OpenAI Prompt Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- Gemini API: [Google AI Studio](https://ai.google.dev/)

---

## 🔗 快速链接

- 📖 [完整文档](./PROJECT_STRUCTURE.md)
- 🚀 [部署指南](./DEPLOY.md)
- 🤖 [机器人配置](./bot/)
- 📊 [选股策略](./select-stocks-guide.md)
- 💡 [交易策略](./trading-strategy.md)
- 🐛 [问题反馈](https://github.com/yourusername/daily_stock_analysis/issues)

---

**提示**: 将此文件保存为书签，随时查阅！
