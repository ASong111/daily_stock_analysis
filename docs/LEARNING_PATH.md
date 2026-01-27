# 🎓 项目学习路线图

> 从零开始，逐步掌握整个项目

---

## 📅 学习计划概览

| 阶段 | 时间 | 目标 | 产出 |
|------|------|------|------|
| 第1天 | 2-3小时 | 环境搭建 + 基础使用 | 能运行分析 |
| 第2-3天 | 4-6小时 | 理解核心模块 | 看懂代码逻辑 |
| 第4-5天 | 4-6小时 | 深入技术细节 | 能修改功能 |
| 第6-7天 | 4-6小时 | 扩展与优化 | 能添加新功能 |

**总计**: 约14-21小时，1周完成

---

## 📚 第1天：环境搭建与基础使用

### 上午 (1-1.5小时)

#### 1. 克隆项目并安装依赖
```bash
git clone https://github.com/yourusername/daily_stock_analysis.git
cd daily_stock_analysis
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

#### 2. 配置环境变量
```bash
cp .env.example .env
vim .env
```

**最小配置**:
```env
# 只配置一个AI服务即可
GEMINI_API_KEY=your_key_here
```

#### 3. 运行第一个分析
```bash
python main.py 600519
```

**预期输出**: 看到贵州茅台的技术分析报告

### 下午 (1-1.5小时)

#### 4. 尝试不同功能
```bash
# 不使用AI分析
python main.py 600519 --no-ai

# 批量分析
python main.py 600519 000001 300750

# 智能选股
python select_stocks.py --days 3 --top 5
```

#### 5. 阅读文档
- [ ] README.md - 了解项目概况
- [ ] docs/QUICK_REFERENCE.md - 快速参考
- [ ] docs/full-guide.md - 完整指南

### 作业
1. 分析3只不同的股票
2. 运行一次智能选股
3. 记录遇到的问题

---

## 📚 第2天：理解数据层

### 上午 (2小时)

#### 1. 学习数据源管理
```bash
# 阅读代码
cat data_provider/__init__.py
cat data_provider/base.py
```

**关键概念**:
- `BaseFetcher`: 数据源基类
- `DataFetcherManager`: 数据管理器
- 多源切换机制
- 优先级管理

#### 2. 实践：测试数据获取
```python
# 创建测试脚本 test_data.py
from data_provider import DataFetcherManager

fetcher = DataFetcherManager()

# 测试获取数据
df, source = fetcher.get_daily_data('600519', days=60)
print(f"数据来源: {source}")
print(f"数据行数: {len(df)}")
print(df.head())
```

### 下午 (2小时)

#### 3. 深入理解数据源
阅读各个数据源实现:
- [ ] `tushare_fetcher.py` - Tushare实现
- [ ] `akshare_fetcher.py` - AKShare实现
- [ ] `efinance_fetcher.py` - EFinance实现

**对比分析**:
| 数据源 | 优点 | 缺点 | 适用场景 |
|--------|------|------|----------|
| Tushare | 数据全面 | 需要积分 | 专业分析 |
| AKShare | 完全免费 | 稳定性一般 | 个人使用 |
| EFinance | 速度快 | 数据有限 | 实时行情 |

#### 4. 练习：添加日志
在数据获取过程中添加详细日志，观察数据流转

### 作业
1. 画出数据获取流程图
2. 测试不同数据源的响应时间
3. 理解故障转移机制

---

## 📚 第3天：理解技术分析

### 上午 (2小时)

#### 1. 学习技术指标
```bash
# 阅读核心代码
cat src/stock_analyzer.py
```

**核心指标**:
- MA (移动平均线)
- MACD (指数平滑异同移动平均线)
- KDJ (随机指标)
- RSI (相对强弱指标)
- BOLL (布林带)

#### 2. 理解趋势判断逻辑
```python
# 多头排列判断
if ma5 > ma10 > ma20 > ma60:
    trend = "强势多头"
elif ma5 > ma10 > ma20:
    trend = "多头排列"
```

### 下午 (2小时)

#### 3. 实践：手动计算指标
```python
# 创建 test_indicators.py
import pandas as pd
from src.stock_analyzer import StockTrendAnalyzer

# 获取数据
from data_provider import DataFetcherManager
fetcher = DataFetcherManager()
df, _ = fetcher.get_daily_data('600519', days=60)

# 分析
analyzer = StockTrendAnalyzer()
result = analyzer.analyze(df, '600519')

# 查看详细结果
print(f"评分: {result.signal_score}")
print(f"趋势: {result.trend_status.value}")
print(f"均线: {result.ma_status.value}")
print(f"MACD: {result.macd_status.value}")
```

#### 4. 可视化指标
使用 matplotlib 绘制K线图和指标

### 作业
1. 理解每个技术指标的含义
2. 手动验证几个指标的计算
3. 分析5只股票，总结规律

---

## 📚 第4天：理解AI分析

### 上午 (2小时)

#### 1. 学习AI分析器
```bash
cat src/analyzer.py
```

**关键概念**:
- Prompt工程
- 上下文构建
- AI模型调用
- 结果解析

#### 2. 理解Prompt设计
```python
# 查看Prompt模板
# 在 analyzer.py 中找到 _build_prompt() 方法
```

### 下午 (2小时)

#### 3. 实践：自定义Prompt
```python
# 修改Prompt，添加自己的分析维度
def _build_custom_prompt(self, context):
    prompt = f"""
    你是一个专业的股票分析师。
    
    股票代码: {context['code']}
    当前价格: {context['today']['close']}
    
    请从以下角度分析:
    1. 技术面
    2. 风险点
    3. 操作建议
    """
    return prompt
```

#### 4. 测试不同AI模型
```bash
# 测试Gemini
GEMINI_API_KEY=xxx python main.py 600519

# 测试Claude
CLAUDE_API_KEY=xxx python main.py 600519
```

### 作业
1. 对比不同AI模型的分析结果
2. 优化Prompt，提高分析质量
3. 添加新的分析维度

---

## 📚 第5天：理解选股逻辑

### 上午 (2小时)

#### 1. 学习选股器
```bash
cat select_stocks.py
```

**选股流程**:
1. 获取热门板块
2. 获取板块成分股
3. 技术面筛选
4. 基本面筛选
5. 排序输出

#### 2. 理解筛选标准
```python
# 技术面标准
- 评分 >= 60
- 多头排列
- 乖离率 < 5%

# 基本面标准
- 市值 50-1000亿
- PE < 100
- ROE > 15%
```

### 下午 (2小时)

#### 3. 实践：自定义选股策略
```python
# 修改筛选条件
def my_filter(candidate):
    # 自定义筛选逻辑
    if candidate.score >= 70:  # 提高评分要求
        if candidate.market_cap >= 100:  # 只要大盘股
            return True
    return False
```

#### 4. 回测选股结果
记录选出的股票，一周后查看涨跌幅

### 作业
1. 设计自己的选股策略
2. 运行选股并记录结果
3. 分析选股成功率

---

## 📚 第6天：机器人与Web服务

### 上午 (2小时)

#### 1. 学习机器人架构
```bash
cat bot/handler.py
cat bot/dispatcher.py
cat bot/commands/analyze.py
```

**架构理解**:
```
消息 → Handler → Dispatcher → Command → 业务逻辑 → 返回
```

#### 2. 配置钉钉机器人
按照 `docs/bot/dingding-bot-config.md` 配置

### 下午 (2小时)

#### 3. 学习Web服务
```bash
cat web/server.py
cat web/handlers.py
```

#### 4. 测试API
```bash
# 启动服务
python web/server.py

# 测试API
curl http://localhost:8080/health
curl http://localhost:8080/analysis?code=600519
```

### 作业
1. 配置一个机器人平台
2. 测试所有机器人命令
3. 设计新的API端点

---

## 📚 第7天：扩展与优化

### 上午 (2小时)

#### 1. 添加新功能
选择一个方向深入:

**方向A: 添加新数据源**
```python
# 实现一个新的数据源
class MyFetcher(BaseFetcher):
    def get_daily_data(self, code, days):
        # 实现逻辑
        pass
```

**方向B: 添加新指标**
```python
# 在 stock_analyzer.py 中添加
def _calculate_my_indicator(self, df):
    # 计算新指标
    pass
```

**方向C: 优化选股策略**
```python
# 添加新的筛选维度
def _check_my_criteria(self, candidate):
    # 自定义标准
    pass
```

### 下午 (2小时)

#### 2. 性能优化
- 添加缓存机制
- 并发处理
- 减少API调用

#### 3. 代码重构
- 提取公共逻辑
- 优化代码结构
- 添加单元测试

### 作业
1. 完成一个新功能
2. 提交Pull Request
3. 写一篇学习总结

---

## 🎯 进阶学习

### 量化交易方向
1. 学习回测框架 (Backtrader)
2. 实现自动交易策略
3. 风险管理系统

### AI方向
1. 深入学习Prompt工程
2. 微调AI模型
3. 多模型集成

### 工程方向
1. 微服务架构
2. 消息队列
3. 分布式部署

---

## 📖 推荐资源

### 技术分析
- 《日本蜡烛图技术》
- 《股市趋势技术分析》
- Investopedia技术分析教程

### Python量化
- 《Python金融大数据分析》
- 《量化投资：以Python为工具》
- QuantConnect教程

### AI应用
- OpenAI Prompt Engineering Guide
- LangChain文档
- Anthropic Claude文档

---

## ✅ 学习检查清单

### 基础知识
- [ ] 理解项目整体架构
- [ ] 掌握基本使用方法
- [ ] 了解各个模块职责

### 核心模块
- [ ] 数据层：多源管理机制
- [ ] 分析层：技术指标计算
- [ ] AI层：Prompt工程
- [ ] 选股层：筛选逻辑

### 实践能力
- [ ] 能独立运行分析
- [ ] 能修改配置参数
- [ ] 能添加新功能
- [ ] 能优化性能

### 进阶能力
- [ ] 设计新的选股策略
- [ ] 集成新的数据源
- [ ] 优化AI分析效果
- [ ] 部署到生产环境

---

## 🎓 学习建议

1. **循序渐进**: 不要跳过基础，扎实掌握每个模块
2. **动手实践**: 每学一个概念，立即写代码验证
3. **记录笔记**: 记录关键概念和遇到的问题
4. **提问交流**: 遇到问题及时在Issue中提问
5. **持续学习**: 关注项目更新，学习新功能

---

**祝学习愉快！有问题随时在GitHub Issues中提问。**
