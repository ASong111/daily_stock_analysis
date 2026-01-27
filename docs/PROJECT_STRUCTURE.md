# 📚 项目结构与快速学习指南

> **项目名称**: A股自选股智能分析系统 (Daily Stock Analysis)
>
> **最后更新**: 2026-01-27

---

## 📋 目录

- [项目概述](#项目概述)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [目录结构](#目录结构)
- [核心模块详解](#核心模块详解)
- [快速上手](#快速上手)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## 🎯 项目概述

这是一个基于 AI 的 A股智能分析系统，提供：
- 📊 **技术分析**: 趋势判断、均线分析、MACD/KDJ指标
- 🤖 **AI 分析**: 集成 Gemini/Claude/OpenAI 进行智能解读
- 📰 **新闻搜索**: 多源新闻搜索（Tavily/SerpAPI/Bocha）
- 🔍 **智能选股**: 热门板块成长股筛选
- 🤖 **机器人集成**: 支持钉钉/飞书/Discord
- 🌐 **Web界面**: 提供HTTP API和Web UI

---

## 🚀 核心功能

### 1. 股票分析
- **技术面分析**: 均线系统、趋势判断、量价关系
- **基本面分析**: 市值、PE、ROE等指标
- **AI智能解读**: 综合分析给出操作建议

### 2. 智能选股
- **热门板块识别**: 自动识别资金流入板块
- **成长股筛选**: 多维度筛选优质标的
- **龙头股推荐**: 板块内龙头股票

### 3. 市场过滤
- **大盘趋势判断**: 上证指数趋势分析
- **风险控制**: 熊市自动停止分析

### 4. 多平台支持
- **机器人**: 钉钉、飞书、Discord
- **Web API**: RESTful API接口
- **命令行**: 本地命令行工具

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户接口层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 钉钉机器人 │  │ 飞书机器人 │  │  Web UI  │  │ 命令行CLI │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    业务逻辑层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 股票分析器 │  │ 智能选股器 │  │ 市场过滤器 │  │ 搜索服务  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    数据层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Tushare  │  │ AKShare  │  │ EFinance │  │ Baostock │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    AI服务层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Gemini  │  │  Claude  │  │  OpenAI  │  │  Tavily  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构

```
daily_stock_analysis/
│
├── 📂 src/                          # 核心源代码
│   ├── analyzer.py                  # AI分析器（Gemini/Claude/OpenAI）
│   ├── stock_analyzer.py            # 技术分析器（趋势/均线/指标）
│   ├── search_service.py            # 新闻搜索服务
│   ├── config.py                    # 配置管理
│   ├── market_filter.py             # 市场过滤器（大盘趋势判断）
│   └── core/                        # 核心工具
│       ├── logger.py                # 日志系统
│       └── utils.py                 # 工具函数
│
├── 📂 data_provider/                # 数据源管理
│   ├── __init__.py                  # 数据管理器（多源切换）
│   ├── base.py                      # 数据源基类
│   ├── tushare_fetcher.py           # Tushare数据源
│   ├── akshare_fetcher.py           # AKShare数据源
│   ├── efinance_fetcher.py          # EFinance数据源
│   ├── baostock_fetcher.py          # Baostock数据源
│   └── yfinance_fetcher.py          # YFinance数据源
│
├── 📂 bot/                          # 机器人模块
│   ├── handler.py                   # 机器人处理器
│   ├── dispatcher.py                # 命令分发器
│   ├── commands/                    # 命令处理
│   │   ├── analyze.py               # 分析命令
│   │   ├── batch.py                 # 批量分析
│   │   ├── market.py                # 市场分析
│   │   └── help.py                  # 帮助命令
│   └── platforms/                   # 平台适配
│       ├── dingtalk.py              # 钉钉机器人
│       ├── feishu_stream.py         # 飞书机器人
│       └── discord.py               # Discord机器人
│
├── 📂 web/                          # Web服务
│   ├── server.py                    # HTTP服务器
│   ├── handlers.py                  # 请求处理器
│   └── static/                      # 静态资源
│
├── 📂 docker/                       # Docker配置
│   ├── Dockerfile                   # Docker镜像
│   └── docker-compose.yml           # 容器编排
│
├── 📂 docs/                         # 文档
│   ├── full-guide.md                # 完整使用指南
│   ├── select-stocks-guide.md       # 选股指南
│   ├── trading-strategy.md          # 交易策略
│   ├── bot/                         # 机器人配置文档
│   └── docker/                      # 部署文档
│
├── 📄 main.py                       # 主程序入口
├── 📄 select_stocks.py              # 智能选股工具
├── 📄 analyzer_service.py           # 分析服务
├── 📄 requirements.txt              # Python依赖
├── 📄 .env.example                  # 环境变量模板
└── 📄 README.md                     # 项目说明

```

---

## 🔍 核心模块详解

### 1. 数据层 (`data_provider/`)

**职责**: 统一管理多个数据源，提供数据获取接口

**核心类**:
- `DataFetcherManager`: 数据管理器，负责多源切换和故障转移
- `BaseFetcher`: 数据源基类，定义统一接口
- `TushareFetcher`, `AkshareFetcher`, etc.: 具体数据源实现

**关键特性**:
- ✅ 多数据源自动切换
- ✅ 故障转移机制
- ✅ 数据格式统一
- ✅ 优先级管理

**使用示例**:
```python
from data_provider import DataFetcherManager

fetcher = DataFetcherManager()
df, source = fetcher.get_daily_data('600519', days=60)
```

---

### 2. 技术分析层 (`src/stock_analyzer.py`)

**职责**: 技术指标计算和趋势判断

**核心类**:
- `StockTrendAnalyzer`: 趋势分析器

**分析维度**:
1. **均线系统**: MA5/MA10/MA20/MA60
2. **趋势判断**: 多头/空头/震荡
3. **技术指标**: MACD、KDJ、RSI、BOLL
4. **量价关系**: 放量/缩量分析
5. **乖离率**: 价格偏离度

**输出结果**:
```python
@dataclass
class TrendAnalysisResult:
    signal_score: int           # 综合评分 0-100
    buy_signal: BuySignal       # 买入信号
    trend_status: TrendStatus   # 趋势状态
    ma_status: MAStatus         # 均线状态
    volume_status: VolumeStatus # 量能状态
    macd_status: MACDStatus     # MACD状态
    kdj_status: KDJStatus       # KDJ状态
    bias_ma5: float            # MA5乖离率
    # ... 更多指标
```

---

### 3. AI分析层 (`src/analyzer.py`)

**职责**: 使用AI模型进行智能分析

**支持的AI模型**:
- 🤖 **Gemini** (Google): 免费额度大，推荐
- 🤖 **Claude** (Anthropic): 分析深度好
- 🤖 **OpenAI** (GPT): 通用性强

**核心类**:
- `GeminiAnalyzer`: Gemini分析器
- `ClaudeAnalyzer`: Claude分析器
- `OpenAIAnalyzer`: OpenAI分析器

**分析流程**:
1. 收集技术指标数据
2. 搜索相关新闻（可选）
3. 构建分析上下文
4. 调用AI模型分析
5. 解析并返回结果

**使用示例**:
```python
from src.analyzer import GeminiAnalyzer

analyzer = GeminiAnalyzer()
context = {
    'code': '600519',
    'date': '2026-01-27',
    'today': {...},  # 当日数据
    'ma_status': '多头排列',
    # ... 更多上下文
}
result = analyzer.analyze(context)
```

---

### 4. 搜索服务层 (`src/search_service.py`)

**职责**: 多源新闻搜索和情报收集

**支持的搜索引擎**:
- 🔍 **Bocha**: 中文优化，AI摘要
- 🔍 **Tavily**: 免费额度1000次/月
- 🔍 **SerpAPI**: 备用方案

**核心功能**:
1. **股票新闻搜索**: `search_stock_news()`
2. **事件搜索**: `search_stock_events()`
3. **多维度情报**: `search_comprehensive_intel()`

**搜索维度**:
- 📰 最新消息
- ⚠️ 风险排查（减持、处罚）
- 📊 业绩预期（年报预告）

---

### 5. 智能选股器 (`select_stocks.py`)

**职责**: 从热门板块中筛选成长股

**选股流程**:
```
1. 获取热门板块 (涨幅前10)
   ↓
2. 获取板块成分股
   ↓
3. 技术面筛选
   - 评分 ≥ 60
   - 多头排列
   - 乖离率 < 5%
   ↓
4. 基本面筛选
   - 市值 50-1000亿
   - PE < 100
   ↓
5. 排序输出
```

**核心类**:
- `HotSectorSelector`: 热门板块选股器

**使用方法**:
```bash
# 基础用法
python select_stocks.py

# 自定义参数
python select_stocks.py --days 3 --top 10 --min-score 60

# 每板块选2只
python select_stocks.py --stocks-per-sector 2
```

**输出**:
- Markdown格式报告
- 包含买入理由、技术分析、基本面数据

---

### 6. 市场过滤器 (`src/market_filter.py`)

**职责**: 大盘趋势判断，熊市风控

**核心功能**:
1. 分析上证指数趋势
2. 判断市场环境（牛市/熊市/震荡）
3. 熊市时停止个股分析

**判断标准**:
- MA5 < MA20 且跌幅 > 2%: 熊市
- MA5 > MA20 且涨幅 > 1%: 牛市
- 其他: 震荡市

---

### 7. 机器人层 (`bot/`)

**职责**: 多平台机器人集成

**支持平台**:
- 💬 钉钉 (DingTalk)
- 💬 飞书 (Feishu)
- 💬 Discord

**命令系统**:
```
/analyze 600519        # 分析单只股票
/batch 600519,000001   # 批量分析
/market                # 大盘分析
/help                  # 帮助信息
```

**架构**:
```
用户消息 → Dispatcher → Command Handler → 业务逻辑 → 返回结果
```

---

### 8. Web服务层 (`web/`)

**职责**: 提供HTTP API和Web界面

**API端点**:
```
GET  /health           # 健康检查
GET  /analysis?code=xxx # 触发分析
POST /webhook          # Webhook接收
```

**特性**:
- ✅ RESTful API
- ✅ CORS支持
- ✅ 异步处理
- ✅ 错误处理

---

## 🚀 快速上手

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/yourusername/daily_stock_analysis.git
cd daily_stock_analysis

# 创建虚拟环境
python -m venv env
source env/bin/activate  # Linux/Mac
# 或
env\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**必需配置**:
```env
# AI分析（至少配置一个）
GEMINI_API_KEY=your_gemini_key
CLAUDE_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key

# 数据源（可选，推荐配置Tushare）
TUSHARE_TOKEN=your_tushare_token

# 搜索服务（可选）
BOCHA_API_KEY=your_bocha_key
TAVILY_API_KEY=your_tavily_key
```

### 3. 运行示例

#### 分析单只股票
```bash
python main.py 600519
```

#### 智能选股
```bash
python select_stocks.py --days 3 --top 10
```

#### 启动Web服务
```bash
python web/server.py
```

#### 启动机器人
```bash
# 钉钉机器人
python -m bot.platforms.dingtalk_stream

# 飞书机器人
python -m bot.platforms.feishu_stream
```

---

## 💻 开发指南

### 代码结构规范

```python
# 1. 导入顺序
import sys                    # 标准库
from pathlib import Path      # 标准库

import pandas as pd           # 第三方库
import numpy as np

from src.config import Config # 本地模块

# 2. 类定义
class MyAnalyzer:
    """分析器类

    职责：
    - 功能1
    - 功能2
    """

    def __init__(self):
        pass

    def analyze(self, data):
        """分析方法

        Args:
            data: 输入数据

        Returns:
            分析结果
        """
        pass

# 3. 函数定义
def helper_function(param: str) -> dict:
    """辅助函数

    Args:
        param: 参数说明

    Returns:
        返回值说明
    """
    pass
```

### 添加新数据源

1. 在 `data_provider/` 创建新文件
2. 继承 `BaseFetcher` 类
3. 实现必需方法：
   - `get_daily_data()`
   - `get_realtime_data()`
4. 在 `__init__.py` 注册

```python
# data_provider/my_fetcher.py
from .base import BaseFetcher

class MyFetcher(BaseFetcher):
    def get_daily_data(self, code, days):
        # 实现逻辑
        pass
```

### 添加新AI模型

1. 在 `src/analyzer.py` 添加新类
2. 继承 `BaseAnalyzer`
3. 实现 `analyze()` 方法

```python
class MyAIAnalyzer(BaseAnalyzer):
    def analyze(self, context):
        # 调用AI API
        # 解析结果
        return result
```

### 添加新机器人平台

1. 在 `bot/platforms/` 创建新文件
2. 继承 `BasePlatform`
3. 实现消息接收和发送

---

## 🔧 配置说明

### 数据源优先级

默认优先级（可在代码中调整）:
1. **EFinance** (Priority 0) - 速度快
2. **Tushare** (Priority 0) - 数据全
3. **AKShare** (Priority 1) - 免费
4. **Baostock** (Priority 3) - 备用
5. **YFinance** (Priority 4) - 国际市场

### AI模型选择

| 模型 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| Gemini | 免费额度大 | 国内访问慢 | 个人使用 |
| Claude | 分析深度好 | 收费 | 专业分析 |
| OpenAI | 通用性强 | 收费较贵 | 企业使用 |

### 搜索引擎选择

| 引擎 | 免费额度 | 特点 | 推荐 |
|------|----------|------|------|
| Bocha | 付费 | 中文优化，AI摘要 | ⭐⭐⭐⭐⭐ |
| Tavily | 1000次/月 | 专为AI优化 | ⭐⭐⭐⭐ |
| SerpAPI | 100次/月 | 真实搜索结果 | ⭐⭐⭐ |

---

## 📊 数据流图

```
用户请求 (股票代码)
    ↓
┌─────────────────┐
│  数据获取层      │
│  DataFetcher    │ → 获取60日K线数据
└─────────────────┘
    ↓
┌─────────────────┐
│  技术分析层      │
│ StockAnalyzer   │ → 计算指标、判断趋势
└─────────────────┘
    ↓
┌─────────────────┐
│  搜索服务层      │
│ SearchService   │ → 搜索相关新闻（可选）
└─────────────────┘
    ↓
┌─────────────────┐
│  AI分析层       │
│  AIAnalyzer     │ → 综合分析、生成建议
└─────────────────┘
    ↓
┌─────────────────┐
│  结果输出       │
│  Formatter      │ → 格式化输出
└─────────────────┘
    ↓
返回给用户
```

---

## 🎓 学习路径

### 初级（1-2天）

1. **了解项目功能**
   - 阅读 `README.md`
   - 运行 `python main.py 600519` 体验功能

2. **理解数据流**
   - 查看 `data_provider/__init__.py`
   - 理解多数据源切换机制

3. **学习技术分析**
   - 阅读 `src/stock_analyzer.py`
   - 理解均线、MACD等指标

### 中级（3-5天）

1. **深入AI分析**
   - 研究 `src/analyzer.py`
   - 理解Prompt工程

2. **学习选股逻辑**
   - 阅读 `select_stocks.py`
   - 理解筛选标准

3. **配置机器人**
   - 按照 `docs/bot/` 文档配置
   - 测试机器人功能

### 高级（1-2周）

1. **自定义策略**
   - 修改选股标准
   - 添加新的技术指标

2. **扩展功能**
   - 添加新数据源
   - 集成新AI模型

3. **性能优化**
   - 添加缓存机制
   - 优化API调用

---

## ❓ 常见问题

### Q1: 数据获取失败怎么办？

**A**: 系统会自动切换数据源。如果所有源都失败：
1. 检查网络连接
2. 确认API Key配置正确
3. 查看 `logs/` 目录日志

### Q2: AI分析返回错误？

**A**: 可能原因：
1. API Key无效或过期
2. 配额用尽
3. 网络问题

解决方法：
```bash
# 检查配置
cat .env | grep API_KEY

# 测试API
python -c "from src.analyzer import GeminiAnalyzer; print(GeminiAnalyzer().is_available())"
```

### Q3: 选股没有结果？

**A**: 可能原因：
1. 筛选标准太严格
2. 板块数据获取失败
3. 当前市场没有符合条件的股票

解决方法：
```bash
# 降低评分标准
python select_stocks.py --min-score 50

# 增加每板块股票数
python select_stocks.py --stocks-per-sector 2
```

### Q4: 如何添加自选股？

**A**: 编辑 `.env` 文件：
```env
STOCK_LIST=600519,000001,300750
```

### Q5: Docker部署问题？

**A**: 参考文档：
- `docs/DEPLOY.md` - 部署指南
- `docs/docker/zeabur-deployment.md` - Zeabur部署

---

## 📚 相关文档

- [完整使用指南](./full-guide.md)
- [选股策略说明](./select-stocks-guide.md)
- [交易策略](./trading-strategy.md)
- [机器人配置](./bot/)
- [部署指南](./DEPLOY.md)
- [贡献指南](./CONTRIBUTING.md)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](../LICENSE) 文件

---

## 📮 联系方式

- 项目主页: https://github.com/yourusername/daily_stock_analysis
- 问题反馈: https://github.com/yourusername/daily_stock_analysis/issues

---

**最后更新**: 2026-01-27
**维护者**: Project Team
