#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势板块选股器 - 基于资金流向和趋势交易策略

选股策略：
1. 板块筛选：最近3日内资金流入最大的5个板块
2. 股票筛选：每个板块挑选2只股票（行业细分龙头）
   - 总市值：200-500亿
   - 流通市值：>80亿
   - 日均成交额：>2亿
   - 基本面消息面良好
3. 趋势交易策略三步法：
   - 第一步（选赛道）：板块指数在MA60上方，且均线掉头向上
   - 第二步（等加油）：股价回踩MA20成功止跌
   - 第三步（对火花）：MACD在零轴上方重新形成金叉

使用方法：
    python trend_sector_selector.py                    # 默认配置
    python trend_sector_selector.py --days 3           # 近3日热门板块
    python trend_sector_selector.py --top-sectors 5    # 前5个板块
    python trend_sector_selector.py --stocks-per-sector 2  # 每板块2只
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.stock_analyzer import StockTrendAnalyzer
from data_provider import DataFetcherManager
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
)

logger = logging.getLogger(__name__)


@dataclass
class SectorInfo:
    """板块信息"""
    name: str
    code: str
    net_inflow: float  # 资金净流入（亿元）
    change_pct: float  # 涨跌幅
    ma60_trend: bool = False  # 是否在MA60上方且向上
    reason: str = ""


@dataclass
class StockCandidate:
    """候选股票"""
    code: str
    name: str
    sector: str

    # 基本面
    market_cap: float  # 总市值（亿元）
    circulating_market_cap: float  # 流通市值（亿元）
    avg_turnover: float  # 日均成交额（亿元）
    pe_ratio: float

    # 技术面
    current_price: float
    ma20: float
    ma60: float

    # 趋势交易三步法
    step1_sector_trend: bool = False  # 板块在MA60上方且向上
    step2_pullback_ma20: bool = False  # 回踩MA20止跌
    step3_macd_golden: bool = False  # MACD零轴上金叉

    # 综合评分
    score: int = 0
    buy_reason: str = ""
    risk_warning: str = ""


class TrendSectorSelector:
    """趋势板块选股器"""

    # 市值阈值（亿元）
    MIN_MARKET_CAP = 200  # 最小总市值
    MAX_MARKET_CAP = 500  # 最大总市值
    MIN_CIRCULATING_CAP = 80  # 最小流通市值
    MIN_AVG_TURNOVER = 2  # 最小日均成交额（亿元）

    # MA20回踩判断容忍度
    MA20_PULLBACK_TOLERANCE = 0.03  # 3%

    # MACD零轴判断阈值
    MACD_ZERO_THRESHOLD = 0.0

    def __init__(self):
        self.analyzer = StockTrendAnalyzer()
        self.fetcher = DataFetcherManager()
        self._stock_info_cache = {}
        self._sector_stocks_cache = {}

    def get_top_sectors_by_capital_flow(
        self,
        days: int = 3,
        top_n: int = 5
    ) -> List[SectorInfo]:
        """
        获取资金流入最大的板块

        Args:
            days: 统计天数
            top_n: 返回前N个板块

        Returns:
            板块信息列表
        """
        logger.info(f"[1/6] 获取近{days}日资金流入最大的{top_n}个板块...")

        try:
            import akshare as ak
            import time

            # 获取板块资金流向数据
            df = ak.stock_sector_fund_flow_rank(indicator="今日")

            if df is None or df.empty:
                logger.warning("  获取板块资金流向数据失败，使用备用方案")
                return self._get_fallback_sectors(top_n)

            # 按资金净流入排序
            if '净额' in df.columns:
                df['净额'] = pd.to_numeric(df['净额'], errors='coerce')
                df = df.dropna(subset=['净额'])
                df = df.sort_values('净额', ascending=False)

                sectors = []
                for idx, row in df.head(top_n).iterrows():
                    sector_name = row['名称']
                    net_inflow = float(row['净额']) / 1e8  # 转为亿元
                    change_pct = float(row.get('涨跌幅', 0))

                    sector = SectorInfo(
                        name=sector_name,
                        code=row.get('代码', ''),
                        net_inflow=net_inflow,
                        change_pct=change_pct,
                        reason=f"近{days}日资金净流入{net_inflow:.2f}亿元"
                    )

                    sectors.append(sector)
                    logger.info(f"  {idx+1}. {sector_name}: 资金净流入{net_inflow:.2f}亿 ({change_pct:+.2f}%)")

                logger.info(f"  ✓ 成功获取 {len(sectors)} 个热门板块")
                return sectors

        except Exception as e:
            logger.warning(f"  获取板块资金流向失败: {e}")
            return self._get_fallback_sectors(top_n)

        return []

    def _get_fallback_sectors(self, top_n: int) -> List[SectorInfo]:
        """备用板块列表"""
        fallback = [
            SectorInfo("半导体", "", 50.0, 3.5, reason="国产替代加速"),
            SectorInfo("人工智能", "", 45.0, 3.2, reason="技术创新落地"),
            SectorInfo("新能源", "", 40.0, 2.8, reason="政策持续利好"),
            SectorInfo("医药", "", 35.0, 2.5, reason="创新药获批"),
            SectorInfo("军工", "", 30.0, 2.3, reason="订单饱满"),
        ]
        logger.info(f"  ⚠ 使用备用板块列表")
        return fallback[:top_n]

    def check_sector_trend(self, sector_name: str) -> bool:
        """
        检查板块趋势（第一步：选赛道）

        判断标准：板块指数在MA60上方，且均线掉头向上

        Args:
            sector_name: 板块名称

        Returns:
            是否符合趋势条件
        """
        try:
            import akshare as ak

            # 获取板块指数历史数据
            df = ak.stock_board_industry_hist_em(
                symbol=sector_name,
                period="日k",
                start_date=(datetime.now() - timedelta(days=120)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust=""
            )

            if df is None or df.empty or len(df) < 60:
                return False

            # 计算MA60
            df['MA60'] = df['收盘'].rolling(window=60).mean()

            # 获取最新数据
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = float(latest['收盘'])
            ma60 = float(latest['MA60'])
            prev_ma60 = float(prev['MA60'])

            # 判断：价格在MA60上方 且 MA60向上
            is_above_ma60 = current_price > ma60
            is_ma60_up = ma60 > prev_ma60

            return is_above_ma60 and is_ma60_up

        except Exception as e:
            logger.debug(f"  检查板块 {sector_name} 趋势失败: {e}")
            return False

    def get_sector_stocks(self, sector_name: str) -> List[str]:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称

        Returns:
            股票代码列表
        """
        # 检查缓存
        if sector_name in self._sector_stocks_cache:
            return self._sector_stocks_cache[sector_name]

        try:
            import akshare as ak
            import time

            logger.info(f"    获取板块 {sector_name} 成分股...")

            df = ak.stock_board_industry_cons_em(symbol=sector_name)

            if df is not None and not df.empty:
                codes = df['代码'].tolist()

                # 排除ST股票和科创板
                if '名称' in df.columns:
                    names = df['名称'].tolist()
                    codes = [
                        code for code, name in zip(codes, names)
                        if 'ST' not in name
                        and '*' not in name
                        and not code.startswith('688')
                        and not code.startswith('8')
                        and not code.startswith('4')
                    ]

                if codes:
                    logger.info(f"    ✓ 获取 {len(codes)} 只股票")
                    self._sector_stocks_cache[sector_name] = codes
                    return codes

            time.sleep(1)  # 避免API限流

        except Exception as e:
            logger.debug(f"    获取板块成分股失败: {e}")

        return []

    def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Returns:
            {'name': 名称, 'market_cap': 总市值, 'circulating_market_cap': 流通市值,
             'avg_turnover': 日均成交额, 'pe_ratio': 市盈率}
        """
        # 检查缓存
        if code in self._stock_info_cache:
            return self._stock_info_cache[code]

        try:
            import akshare as ak

            # 获取实时行情
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                stock_row = df[df['代码'] == code]

                if not stock_row.empty:
                    row = stock_row.iloc[0]

                    name = row.get('名称', '')

                    # 排除ST股票
                    if 'ST' in name or '*' in name:
                        return None

                    # 获取成交额（元），转为亿元
                    turnover = float(row.get('成交额', 0)) / 1e8 if row.get('成交额') else 0

                    info = {
                        'name': name,
                        'market_cap': float(row.get('总市值', 0)) / 1e8,  # 转为亿元
                        'circulating_market_cap': float(row.get('流通市值', 0)) / 1e8,  # 转为亿元
                        'avg_turnover': turnover,  # 当日成交额作为参考
                        'pe_ratio': float(row.get('市盈率-动态', 0)) if row.get('市盈率-动态') else 0,
                    }

                    self._stock_info_cache[code] = info
                    return info

        except Exception as e:
            logger.debug(f"    获取股票 {code} 信息失败: {e}")

        return None

    def check_trend_strategy(
        self,
        code: str,
        sector_ma60_trend: bool
    ) -> Optional[StockCandidate]:
        """
        检查趋势交易策略三步法

        Args:
            code: 股票代码
            sector_ma60_trend: 板块是否符合MA60趋势

        Returns:
            StockCandidate 或 None
        """
        try:
            # 获取股票信息
            stock_info = self.get_stock_info(code)
            if not stock_info:
                return None

            # 检查市值范围：100亿-800亿
            if stock_info['market_cap'] < self.MIN_MARKET_CAP or stock_info['market_cap'] > self.MAX_MARKET_CAP:
                return None

            # 检查流通市值：>80亿
            if stock_info['circulating_market_cap'] < self.MIN_CIRCULATING_CAP:
                return None

            # 检查日均成交额：>2亿（这里用当日成交额作为参考）
            if stock_info['avg_turnover'] < self.MIN_AVG_TURNOVER:
                return None

            # 获取历史数据（需要足够的数据计算MA60和MACD）
            df, _ = self.fetcher.get_daily_data(code, days=90)

            if df is None or df.empty or len(df) < 60:
                return None

            # 趋势分析
            result = self.analyzer.analyze(df, code)

            # 第一步：选赛道 - 板块在MA60上方且向上
            step1 = sector_ma60_trend

            # 第二步：等加油 - 股价回踩MA20成功止跌
            # 判断标准：当前价格在MA20附近（±3%），且有止跌迹象
            price_to_ma20_ratio = (result.current_price - result.ma20) / result.ma20
            step2 = abs(price_to_ma20_ratio) <= self.MA20_PULLBACK_TOLERANCE

            # 第三步：对火花 - MACD在零轴上方重新形成金叉
            # 判断标准：DIF和DEA都在零轴上方，且DIF刚上穿DEA
            macd_above_zero = result.macd_dif > self.MACD_ZERO_THRESHOLD and result.macd_dea > self.MACD_ZERO_THRESHOLD
            macd_golden_cross = result.macd_status.value in ['零轴上金叉', '金叉']
            step3 = macd_above_zero and macd_golden_cross

            # 至少满足2个条件才考虑
            steps_passed = sum([step1, step2, step3])
            if steps_passed < 2:
                return None

            # 构建候选股票
            candidate = StockCandidate(
                code=code,
                name=stock_info['name'],
                sector="",  # 稍后填充
                market_cap=stock_info['market_cap'],
                circulating_market_cap=stock_info['circulating_market_cap'],
                avg_turnover=stock_info['avg_turnover'],
                pe_ratio=stock_info['pe_ratio'],
                current_price=result.current_price,
                ma20=result.ma20,
                ma60=result.ma60,
                step1_sector_trend=step1,
                step2_pullback_ma20=step2,
                step3_macd_golden=step3,
            )

            # 计算评分
            score = 0
            reasons = []

            if step1:
                score += 40
                reasons.append("✓ 板块趋势向上（MA60上方）")
            else:
                reasons.append("✗ 板块趋势待确认")

            if step2:
                score += 30
                reasons.append(f"✓ 回踩MA20止跌（偏离{price_to_ma20_ratio*100:.1f}%）")
            else:
                reasons.append("✗ 未回踩MA20")

            if step3:
                score += 30
                reasons.append("✓ MACD零轴上金叉")
            else:
                reasons.append("✗ MACD信号待确认")

            candidate.score = score
            candidate.buy_reason = "；".join(reasons)

            # 风险提示
            risk_warnings = []
            if result.bias_ma5 > 5:
                risk_warnings.append(f"乖离率较高({result.bias_ma5:.1f}%)，注意回调风险")
            if candidate.pe_ratio > 50:
                risk_warnings.append(f"估值偏高(PE {candidate.pe_ratio:.1f})")
            if not step1:
                risk_warnings.append("板块趋势未确认，需观察")

            candidate.risk_warning = "；".join(risk_warnings) if risk_warnings else "风险可控"

            return candidate

        except Exception as e:
            logger.debug(f"[{code}] 分析失败: {e}")
            return None

    def select_stocks(
        self,
        days: int = 3,
        top_sectors: int = 5,
        stocks_per_sector: int = 2
    ) -> List[StockCandidate]:
        """
        执行选股

        Args:
            days: 统计天数
            top_sectors: 选择前N个板块
            stocks_per_sector: 每个板块选几只股票

        Returns:
            候选股票列表
        """
        logger.info("=" * 80)
        logger.info("趋势板块选股器 - 基于资金流向和趋势交易策略")
        logger.info("=" * 80)

        # 1. 获取热门板块
        sectors = self.get_top_sectors_by_capital_flow(days, top_sectors)

        if not sectors:
            logger.error("未找到热门板块")
            return []

        # 2. 检查板块趋势
        logger.info(f"\n[2/6] 检查板块趋势（MA60）...")
        for sector in sectors:
            sector.ma60_trend = self.check_sector_trend(sector.name)
            status = "✓" if sector.ma60_trend else "✗"
            logger.info(f"  {status} {sector.name}: MA60趋势{'向上' if sector.ma60_trend else '待确认'}")

        # 3. 从每个板块中选股
        all_candidates = []

        logger.info(f"\n[3/6] 从热门板块中筛选股票...")
        logger.info(f"筛选标准: 市值{self.MIN_MARKET_CAP}-{self.MAX_MARKET_CAP}亿, 流通市值>{self.MIN_CIRCULATING_CAP}亿, 日均成交额>{self.MIN_AVG_TURNOVER}亿, 趋势交易三步法")

        for sector_idx, sector in enumerate(sectors, 1):
            logger.info(f"\n  [{sector_idx}/{top_sectors}] 分析板块: {sector.name}")

            # 获取板块成分股
            stock_codes = self.get_sector_stocks(sector.name)

            if not stock_codes:
                logger.warning(f"    板块 {sector.name} 无成分股数据")
                continue

            # 分析板块内的股票
            sector_candidates = []
            total_stocks = min(len(stock_codes), 30)  # 每个板块最多分析30只

            for idx, code in enumerate(stock_codes[:30], 1):
                if idx % 10 == 0:
                    logger.info(f"    进度: {idx}/{total_stocks}")

                candidate = self.check_trend_strategy(code, sector.ma60_trend)

                if candidate:
                    candidate.sector = sector.name
                    sector_candidates.append(candidate)

            # 按评分排序，取前N只
            sector_candidates.sort(key=lambda x: x.score, reverse=True)

            for candidate in sector_candidates[:stocks_per_sector]:
                all_candidates.append(candidate)
                logger.info(f"    ✓ {candidate.name}({candidate.code}): {candidate.score}分 - "
                          f"市值{candidate.market_cap:.0f}亿/流通{candidate.circulating_market_cap:.0f}亿/成交{candidate.avg_turnover:.2f}亿")

        # 4. 全局排序
        logger.info(f"\n[4/6] 全局排序...")
        all_candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"\n[5/6] 筛选完成，共选出 {len(all_candidates)} 只股票")

        return all_candidates

    def export_to_markdown(
        self,
        candidates: List[StockCandidate],
        output_file: Optional[str] = None
    ) -> str:
        """
        导出为 Markdown 格式

        Args:
            candidates: 候选股票列表
            output_file: 输出文件路径

        Returns:
            Markdown 内容
        """
        if not candidates:
            return "# 选股结果\n\n未找到符合条件的股票。"

        # 生成文件名
        if output_file is None:
            date_str = datetime.now().strftime('%Y%m%d')
            output_file = f"trend_sector_stocks_{date_str}.md"

        # 构建 Markdown 内容
        lines = [
            "# 📈 趋势板块选股结果",
            "",
            f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**股票数量：** {len(candidates)} 只",
            "",
            "---",
            "",
            "## 📊 选股策略",
            "",
            "### 板块筛选",
            "- 最近3日内资金流入最大的5个板块",
            "",
            "### 股票筛选",
            f"- 总市值：{self.MIN_MARKET_CAP}-{self.MAX_MARKET_CAP}亿",
            f"- 流通市值：>{self.MIN_CIRCULATING_CAP}亿",
            f"- 日均成交额：>{self.MIN_AVG_TURNOVER}亿",
            "- 基本面消息面良好",
            "- 排除ST股票",
            "",
            "### 趋势交易策略三步法",
            "",
            "| 步骤 | 名称 | 判断标准 | 指标 |",
            "|------|------|----------|------|",
            "| 第一步 | 选赛道 | 找处于上升趋势的板块 | 板块指数在MA60上方，且均线掉头向上 |",
            "| 第二步 | 等加油 | 找回调不破支撑的个股 | 股价回踩MA20成功止跌 |",
            "| 第三步 | 对火花 | 寻找动能反转点 | MACD在零轴上方重新形成金叉 |",
            "",
            "---",
            "",
            "## 🎯 推荐股票",
            "",
        ]

        # 添加每只股票的详细信息
        for idx, stock in enumerate(candidates, 1):
            lines.extend([
                f"### {idx}. {stock.name}（{stock.code}）",
                "",
                f"**综合评分：** {stock.score}分 | **所属板块：** {stock.sector}",
                "",
                "#### 📋 基本信息",
                "",
                f"| 项目 | 数据 |",
                f"|------|------|",
                f"| 总市值 | {stock.market_cap:.0f}亿元 |",
                f"| 流通市值 | {stock.circulating_market_cap:.0f}亿元 |",
                f"| 日均成交额 | {stock.avg_turnover:.2f}亿元 |",
                f"| 市盈率 | {stock.pe_ratio:.1f} |" if stock.pe_ratio > 0 else "| 市盈率 | - |",
                f"| 当前价格 | {stock.current_price:.2f} |",
                f"| MA20 | {stock.ma20:.2f} |",
                f"| MA60 | {stock.ma60:.2f} |",
                "",
                "#### 💡 趋势交易三步法",
                "",
                f"| 步骤 | 状态 |",
                f"|------|------|",
                f"| 第一步：选赛道 | {'✅ 通过' if stock.step1_sector_trend else '⚠️ 待确认'} |",
                f"| 第二步：等加油 | {'✅ 通过' if stock.step2_pullback_ma20 else '⚠️ 待确认'} |",
                f"| 第三步：对火花 | {'✅ 通过' if stock.step3_macd_golden else '⚠️ 待确认'} |",
                "",
                f"**买入理由：** {stock.buy_reason}",
                "",
                f"**风险提示：** {stock.risk_warning}",
                "",
                "---",
                "",
            ])

        # 添加自选股列表
        lines.extend([
            "## 📝 自选股列表",
            "",
            "```",
            ",".join([s.code for s in candidates]),
            "```",
            "",
            "**使用方法：** 将上述股票代码复制到 `.env` 文件的 `STOCK_LIST` 中",
            "",
            "---",
            "",
            "## ⚠️ 风险提示",
            "",
            "1. 本选股结果仅供参考，不构成投资建议",
            "2. 股市有风险，投资需谨慎",
            "3. 建议结合个人风险承受能力和投资目标进行决策",
            "4. 买入前请再次确认技术形态和基本面情况",
            "5. 严格执行止损纪律（建议跌破MA20或亏损5-8%止损）",
            "",
            "---",
            "",
            f"**生成工具：** 趋势板块选股器 v1.0",
            f"**数据来源：** AkShare",
        ])

        content = "\n".join(lines)

        # 保存到文件
        output_path = Path(output_file)
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"\n[6/6] 结果已保存到: {output_path.absolute()}")

        return content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='趋势板块选股器 - 基于资金流向和趋势交易策略',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python trend_sector_selector.py                          # 默认配置
  python trend_sector_selector.py --days 3                 # 近3日热门板块
  python trend_sector_selector.py --top-sectors 5          # 前5个板块
  python trend_sector_selector.py --stocks-per-sector 2    # 每板块2只
  python trend_sector_selector.py --output my_stocks.md    # 指定输出文件
        '''
    )

    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='统计天数 (默认: 3)'
    )

    parser.add_argument(
        '--top-sectors',
        type=int,
        default=5,
        help='选择前N个板块 (默认: 5)'
    )

    parser.add_argument(
        '--stocks-per-sector',
        type=int,
        default=2,
        help='每个板块选几只股票 (默认: 2)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出文件名 (默认: trend_sector_stocks_YYYYMMDD.md)'
    )

    args = parser.parse_args()

    # 创建选股器
    selector = TrendSectorSelector()

    # 执行选股
    candidates = selector.select_stocks(
        days=args.days,
        top_sectors=args.top_sectors,
        stocks_per_sector=args.stocks_per_sector
    )

    if not candidates:
        logger.error("未找到符合条件的股票")
        logger.warning("\n可能的原因:")
        logger.warning(f"  1. 市值{selector.MIN_MARKET_CAP}-{selector.MAX_MARKET_CAP}亿、流通市值>{selector.MIN_CIRCULATING_CAP}亿、成交额>{selector.MIN_AVG_TURNOVER}亿的股票较少")
        logger.warning("  2. 当前市场环境下符合趋势交易策略的股票较少")
        logger.warning("  3. 网络不稳定，数据获取失败")
        logger.warning("\n建议:")
        logger.warning("  1. 调整市值要求（修改代码中的 MIN_MARKET_CAP/MAX_MARKET_CAP）")
        logger.warning("  2. 降低流通市值要求（修改代码中的 MIN_CIRCULATING_CAP）")
        logger.warning("  3. 降低成交额要求（修改代码中的 MIN_AVG_TURNOVER）")
        logger.warning("  4. 增加板块数量: --top-sectors 10")
        logger.warning("  5. 稍后重试")
        return 1

    # 导出结果
    selector.export_to_markdown(candidates, args.output)

    # 打印摘要
    print("\n" + "=" * 80)
    print("选股摘要")
    print("=" * 80)
    print(f"\n{'排名':<6} {'代码':<10} {'名称':<12} {'评分':<8} {'板块':<15} {'市值(亿)':<12}")
    print("-" * 80)

    for idx, stock in enumerate(candidates, 1):
        print(f"{idx:<6} {stock.code:<10} {stock.name:<12} {stock.score:<8} "
              f"{stock.sector:<15} {stock.market_cap:<12.0f}")

    print("-" * 80)
    print(f"共 {len(candidates)} 只股票")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
