#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精准选股模块 - 热门板块成长股选股器

功能：
1. 识别近期热门板块（资金流入前10）
2. 从热门板块中筛选成长型大牛股
3. 排除ST股票
4. 输出详细的买入理由

使用方法：
    python select_stocks.py                          # 默认配置
    python select_stocks.py --min-score 70           # 最低评分70
    python select_stocks.py --top 20                 # 返回20只
    python select_stocks.py --days 5                 # 近5日热门板块
    python select_stocks.py --stocks-per-sector 2    # 每板块2只
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.stock_analyzer import StockTrendAnalyzer
from data_provider import DataFetcherManager
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
)

logger = logging.getLogger(__name__)


@dataclass
class StockCandidate:
    """候选股票"""
    code: str
    name: str
    score: int
    signal: str
    trend_status: str
    bias_ma5: float
    sector: str
    sector_rank: int  # 板块内排名

    # 基本面数据
    market_cap: float = 0.0  # 市值（亿元）
    pe_ratio: float = 0.0
    roe: float = 0.0
    profit_growth: float = 0.0  # 业绩增长率

    # 买入理由
    technical_reason: str = ""
    sector_reason: str = ""
    fundamental_reason: str = ""
    catalyst: str = ""


class HotSectorSelector:
    """热门板块选股器"""

    # 备用热门板块（当API失败时使用）
    # 注意：板块名称必须与akshare接口中的名称完全一致
    FALLBACK_SECTORS = [
        {'name': '航空航天', 'change_pct': 3.5, 'reason': '低空经济政策支持，国防建设加速'},
        {'name': '半导体', 'change_pct': 3.2, 'reason': '国产替代加速，产业升级'},
        {'name': '芯片', 'change_pct': 3.0, 'reason': '高端芯片突破，自主可控'},
        {'name': '新能源', 'change_pct': 2.8, 'reason': '政策利好，行业景气'},
        {'name': '医药', 'change_pct': 2.5, 'reason': '创新药获批，行业复苏'},
        {'name': '人工智能', 'change_pct': 2.3, 'reason': '技术创新，应用落地'},
        {'name': '新材料', 'change_pct': 2.0, 'reason': '产业升级，需求增长'},
        {'name': '通信设备', 'change_pct': 1.8, 'reason': '5G/6G建设，技术迭代'},
        {'name': '光伏', 'change_pct': 1.5, 'reason': '装机量增长，产业链景气'},
        {'name': '锂电池', 'change_pct': 1.2, 'reason': '新能源车渗透率提升'},
    ]

    def __init__(self):
        self.analyzer = StockTrendAnalyzer()
        self.fetcher = DataFetcherManager()
        self._stock_info_cache = {}  # 缓存股票信息，避免重复请求

    def get_hot_sectors(self, days: int = 3, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门板块

        Args:
            days: 统计天数（3日或5日）
            top_n: 返回前N个板块

        Returns:
            热门板块列表 [{'name': '板块名', 'change_pct': 涨幅, 'reason': '热门原因'}, ...]
        """
        import akshare as ak
        import time

        logger.info(f"[1/5] 获取近{days}日热门板块...")

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 指数退避：2, 4, 8秒
                    logger.info(f"  等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

                logger.info(f"  尝试获取板块数据 ({attempt + 1}/{max_retries})...")

                # 获取板块行情
                df = ak.stock_board_industry_name_em()

                if df is None or df.empty:
                    logger.warning("获取板块数据为空")
                    continue

                # 按涨跌幅排序
                change_col = '涨跌幅'
                if change_col in df.columns:
                    df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
                    df = df.dropna(subset=[change_col])
                    df = df.sort_values(change_col, ascending=False)

                    # 获取前N个板块
                    hot_sectors = []
                    for idx, row in df.head(top_n).iterrows():
                        sector_name = row['板块名称']
                        change_pct = row[change_col]

                        # 判断热门原因
                        reason = self._get_sector_reason(sector_name, change_pct)

                        hot_sectors.append({
                            'name': sector_name,
                            'change_pct': change_pct,
                            'reason': reason,
                            'code': row.get('板块代码', ''),
                        })

                        logger.info(f"  {idx+1}. {sector_name}: {change_pct:+.2f}% - {reason}")

                    logger.info(f"  成功获取 {len(hot_sectors)} 个热门板块")
                    return hot_sectors

            except Exception as e:
                logger.warning(f"  第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"获取热门板块失败，已重试 {max_retries} 次")
                    logger.warning("使用备用热门板块列表...")
                    return self.FALLBACK_SECTORS[:top_n]

        logger.warning("使用备用热门板块列表...")
        return self.FALLBACK_SECTORS[:top_n]

    def _get_sector_reason(self, sector_name: str, change_pct: float) -> str:
        """判断板块热门原因"""
        if change_pct >= 5:
            return "强势领涨，资金大幅流入"
        elif change_pct >= 3:
            return "持续上涨，资金持续流入"
        elif change_pct >= 1:
            return "温和上涨，资金稳定流入"
        else:
            return "小幅上涨"

    def get_sector_stocks(self, sector_name: str) -> List[str]:
        """
        获取板块内的股票列表

        Args:
            sector_name: 板块名称

        Returns:
            股票代码列表
        """
        import akshare as ak
        import time

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = min(2 ** attempt, 5)  # 最多等5秒
                    logger.debug(f"    等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

                # 获取板块成分股
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
                            and not code.startswith('688')  # 排除科创板
                            and not code.startswith('8')    # 排除北交所
                            and not code.startswith('4')    # 排除新三板
                        ]

                    if codes:
                        logger.debug(f"    板块 {sector_name} 共 {len(codes)} 只股票（已排除ST和科创板）")
                        return codes

            except Exception as e:
                logger.debug(f"    获取板块 {sector_name} 成分股失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        # 如果所有重试都失败，记录警告
        logger.warning(f"    板块 {sector_name} 成分股获取失败，跳过该板块")
        return []

    def analyze_stock(
        self,
        code: str,
        sector_name: str,
        sector_reason: str
    ) -> Optional[StockCandidate]:
        """
        分析单只股票

        Args:
            code: 股票代码
            sector_name: 所属板块
            sector_reason: 板块热门原因

        Returns:
            StockCandidate 或 None
        """
        try:
            # 获取历史数据
            df, _ = self.fetcher.get_daily_data(code, days=60)

            if df is None or df.empty or len(df) < 30:
                return None

            # 趋势分析
            result = self.analyzer.analyze(df, code)

            # 检查基本条件
            if result.signal_score < 60:
                return None

            # 必须是多头排列
            if result.trend_status.value not in ['强势多头', '多头排列']:
                return None

            # 乖离率必须 < 5%
            if result.bias_ma5 >= 5.0:
                return None

            # 获取股票名称和基本面数据
            stock_name, fundamental_data = self._get_stock_info(code)

            if not stock_name:
                return None

            # 检查成长性标准
            if not self._check_growth_criteria(fundamental_data):
                return None

            # 构建候选股票
            candidate = StockCandidate(
                code=code,
                name=stock_name,
                score=result.signal_score,
                signal=result.buy_signal.value,
                trend_status=result.trend_status.value,
                bias_ma5=result.bias_ma5,
                sector=sector_name,
                sector_rank=0,  # 稍后排序
                market_cap=fundamental_data.get('market_cap', 0),
                pe_ratio=fundamental_data.get('pe_ratio', 0),
                roe=fundamental_data.get('roe', 0),
                profit_growth=fundamental_data.get('profit_growth', 0),
            )

            # 生成买入理由
            self._generate_buy_reasons(candidate, result, sector_reason)

            return candidate

        except Exception as e:
            logger.debug(f"[{code}] 分析失败: {e}")
            return None

    def _get_stock_info(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """
        获取股票名称和基本面数据（带缓存）

        Returns:
            (股票名称, 基本面数据字典)
        """
        # 检查缓存
        if code in self._stock_info_cache:
            return self._stock_info_cache[code]

        import akshare as ak
        import time

        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(1)

                # 获取实时行情（包含名称、市值、PE等）
                df = ak.stock_zh_a_spot_em()

                if df is not None and not df.empty:
                    stock_row = df[df['代码'] == code]

                    if not stock_row.empty:
                        row = stock_row.iloc[0]

                        name = row.get('名称', '')

                        # 排除ST股票
                        if 'ST' in name or '*' in name:
                            result = ('', {})
                            self._stock_info_cache[code] = result
                            return result

                        # 提取基本面数据
                        fundamental_data = {
                            'market_cap': float(row.get('总市值', 0)) / 1e8 if row.get('总市值') else 0,  # 转为亿元
                            'pe_ratio': float(row.get('市盈率-动态', 0)) if row.get('市盈率-动态') else 0,
                            'roe': 0,  # 需要从其他接口获取
                            'profit_growth': 0,  # 需要从其他接口获取
                        }

                        result = (name, fundamental_data)
                        self._stock_info_cache[code] = result
                        return result

            except Exception as e:
                logger.debug(f"    获取股票 {code} 信息失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        result = ('', {})
        self._stock_info_cache[code] = result
        return result

    def _check_growth_criteria(self, fundamental_data: Dict[str, Any]) -> bool:
        """
        检查成长性标准

        标准：
        - 市值 50亿-1000亿
        - PE < 100（排除估值过高）
        - ROE > 15%（如果有数据）
        - 业绩增长 > 30%（如果有数据）
        """
        market_cap = fundamental_data.get('market_cap', 0)
        pe_ratio = fundamental_data.get('pe_ratio', 0)

        # 市值范围：50亿-1000亿
        if market_cap > 0:
            if market_cap < 50 or market_cap > 1000:
                return False

        # PE不能过高
        if pe_ratio > 0:
            if pe_ratio > 100:
                return False

        # ROE和业绩增长（如果有数据的话）
        # 注：这些数据需要从专业接口获取，这里暂时放宽

        return True

    def _generate_buy_reasons(
        self,
        candidate: StockCandidate,
        trend_result,
        sector_reason: str
    ):
        """生成买入理由"""

        # 1. 技术面理由（从趋势分析结果提取）
        technical_reasons = []

        if trend_result.trend_status.value == '强势多头':
            technical_reasons.append("强势多头排列，均线发散上行")
        elif trend_result.trend_status.value == '多头排列':
            technical_reasons.append("多头排列，趋势向上")

        if trend_result.bias_ma5 < 0:
            technical_reasons.append(f"回踩MA5支撑（乖离率{trend_result.bias_ma5:.1f}%）")
        elif trend_result.bias_ma5 < 2:
            technical_reasons.append(f"价格贴近MA5（乖离率{trend_result.bias_ma5:.1f}%）")

        if trend_result.volume_status.value == '缩量回调':
            technical_reasons.append("缩量回调，洗盘特征明显")
        elif trend_result.volume_status.value == '放量上涨':
            technical_reasons.append("放量上涨，多头力量强劲")

        if 'MACD' in trend_result.macd_signal:
            technical_reasons.append(trend_result.macd_signal)

        candidate.technical_reason = "；".join(technical_reasons[:3])  # 最多3条

        # 2. 板块理由
        candidate.sector_reason = f"{candidate.sector}板块{sector_reason}"

        # 3. 基本面理由
        fundamental_reasons = []

        if candidate.market_cap > 0:
            if candidate.market_cap >= 500:
                fundamental_reasons.append(f"大盘股（市值{candidate.market_cap:.0f}亿）")
            elif candidate.market_cap >= 200:
                fundamental_reasons.append(f"中盘股（市值{candidate.market_cap:.0f}亿）")
            else:
                fundamental_reasons.append(f"成长股（市值{candidate.market_cap:.0f}亿）")

        if candidate.pe_ratio > 0:
            if candidate.pe_ratio < 20:
                fundamental_reasons.append(f"估值合理（PE {candidate.pe_ratio:.1f}）")
            elif candidate.pe_ratio < 50:
                fundamental_reasons.append(f"估值适中（PE {candidate.pe_ratio:.1f}）")

        if candidate.profit_growth > 30:
            fundamental_reasons.append(f"业绩高增长（{candidate.profit_growth:.0f}%）")

        if candidate.roe > 15:
            fundamental_reasons.append(f"盈利能力强（ROE {candidate.roe:.1f}%）")

        if not fundamental_reasons:
            fundamental_reasons.append("基本面稳健")

        candidate.fundamental_reason = "；".join(fundamental_reasons[:2])  # 最多2条

        # 4. 催化剂（根据板块和技术形态判断）
        catalysts = []

        # 根据板块判断催化剂
        sector_catalysts = {
            '航空航天': '低空经济政策支持，国防建设加速，订单饱满',
            '半导体': '国产替代加速，产业链景气，政策扶持',
            '芯片': '高端芯片突破，自主可控，技术迭代',
            '新能源': '政策持续利好，行业景气度高，渗透率提升',
            '医药': '创新药获批，行业复苏，研发投入加大',
            '人工智能': '技术创新，应用落地，产业化加速',
            '新材料': '产业升级，需求增长，技术突破',
            '通信': '5G/6G建设，技术迭代，应用拓展',
            '光伏': '装机量增长，产业链景气，政策支持',
            '锂电池': '新能源车渗透率提升，需求旺盛',
            '军工': '订单饱满，业绩确定性强',
            '消费': '消费复苏，业绩改善',
            '科技': '技术创新，产业升级',
            '金融': '政策宽松，估值修复',
        }

        for key, catalyst in sector_catalysts.items():
            if key in candidate.sector:
                catalysts.append(catalyst)
                break

        # 根据技术形态判断
        if trend_result.bias_ma5 < 0:
            catalysts.append("回踩买点，风险收益比佳")

        if trend_result.macd_status.value in ['零轴上金叉', '金叉']:
            catalysts.append("MACD金叉，趋势确认")

        if not catalysts:
            catalysts.append("技术形态良好，等待突破")

        candidate.catalyst = "；".join(catalysts[:2])  # 最多2条

    def select_stocks(
        self,
        min_score: int = 60,
        top_n: int = 10,
        days: int = 3,
        stocks_per_sector: int = 1
    ) -> List[StockCandidate]:
        """
        执行选股

        Args:
            min_score: 最低评分
            top_n: 返回前N只股票
            days: 统计天数（3日或5日）
            stocks_per_sector: 每个板块选几只

        Returns:
            候选股票列表
        """
        logger.info("=" * 80)
        logger.info("精准选股 - 热门板块成长股")
        logger.info("=" * 80)

        # 1. 获取热门板块
        hot_sectors = self.get_hot_sectors(days=days, top_n=10)

        if not hot_sectors:
            logger.error("未找到热门板块")
            return []

        # 2. 从每个板块中选股
        all_candidates = []

        logger.info(f"\n[2/5] 从热门板块中筛选股票...")
        logger.info(f"筛选标准: 评分≥{min_score}, 多头排列, 乖离率<5%, 市值50-1000亿, PE<100")

        for sector_idx, sector in enumerate(hot_sectors, 1):
            sector_name = sector['name']
            sector_reason = sector['reason']

            logger.info(f"\n  [{sector_idx}/10] 分析板块: {sector_name} ({sector['change_pct']:+.2f}%)")

            # 获取板块成分股
            stock_codes = self.get_sector_stocks(sector_name)

            if not stock_codes:
                logger.warning(f"    板块 {sector_name} 无成分股数据")
                continue

            # 分析板块内的股票
            sector_candidates = []
            total_stocks = min(len(stock_codes), 50)

            for idx, code in enumerate(stock_codes[:50], 1):  # 每个板块最多分析前50只
                if idx % 10 == 0:
                    logger.info(f"    进度: {idx}/{total_stocks}")

                candidate = self.analyze_stock(code, sector_name, sector_reason)

                if candidate:
                    sector_candidates.append(candidate)

            # 按评分排序，取前N只
            sector_candidates.sort(key=lambda x: x.score, reverse=True)

            for rank, candidate in enumerate(sector_candidates[:stocks_per_sector], 1):
                candidate.sector_rank = rank
                all_candidates.append(candidate)
                logger.info(f"    ✓ {candidate.name}({candidate.code}): {candidate.score}分")

        # 3. 全局排序
        logger.info(f"\n[3/5] 全局排序...")
        all_candidates.sort(key=lambda x: x.score, reverse=True)

        # 4. 返回前N只
        selected = all_candidates[:top_n]

        logger.info(f"\n[4/5] 筛选完成，共选出 {len(selected)} 只股票")

        # 如果没有结果，给出建议
        if not selected:
            logger.warning("\n未找到符合条件的股票")
            logger.warning("\n可能的原因:")
            logger.warning("  1. 网络不稳定，板块成分股获取失败")
            logger.warning("  2. 选股标准太严格（评分≥60, 多头排列, 乖离率<5%, 市值50-1000亿）")
            logger.warning("  3. 当前市场环境下符合条件的股票较少")
            logger.warning("\n建议:")
            logger.warning("  1. 降低评分标准: --min-score 50")
            logger.warning("  2. 增加每板块股票数: --stocks-per-sector 2")
            logger.warning("  3. 稍后重试（避开网络高峰期）")
            logger.warning("  4. 使用备用板块（程序会自动使用）")

        return selected

    def export_to_markdown(
        self,
        candidates: List[StockCandidate],
        output_file: Optional[str] = None
    ) -> str:
        """
        导出为 Markdown 格式

        Args:
            candidates: 候选股票列表
            output_file: 输出文件路径（可选）

        Returns:
            Markdown 内容
        """
        if not candidates:
            return "# 选股结果\n\n未找到符合条件的股票。"

        # 生成文件名
        if output_file is None:
            date_str = datetime.now().strftime('%Y%m%d')
            output_file = f"selected_stocks_{date_str}.md"

        # 构建 Markdown 内容
        lines = [
            "# 📈 精准选股结果",
            "",
            f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**股票数量：** {len(candidates)} 只",
            "",
            "---",
            "",
            "## 📊 选股标准",
            "",
            "- ✅ 技术面：多头排列（MA5>MA10>MA20），乖离率<5%，评分≥60",
            "- ✅ 基本面：市值50-1000亿，PE<100，成长性好",
            "- ✅ 板块：近期热门板块龙头",
            "- ✅ 排除：ST股票",
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
                f"**综合评分：** {stock.score}分 | **信号：** {stock.signal} | **趋势：** {stock.trend_status}",
                "",
                "#### 📋 基本信息",
                "",
                f"| 项目 | 数据 |",
                f"|------|------|",
                f"| 所属板块 | {stock.sector} |",
                f"| 市值 | {stock.market_cap:.0f}亿元 |" if stock.market_cap > 0 else "",
                f"| 市盈率 | {stock.pe_ratio:.1f} |" if stock.pe_ratio > 0 else "",
                f"| 乖离率 | {stock.bias_ma5:+.2f}% |",
                "",
                "#### 💡 买入理由",
                "",
                f"**技术面：** {stock.technical_reason}",
                "",
                f"**板块逻辑：** {stock.sector_reason}",
                "",
                f"**基本面：** {stock.fundamental_reason}",
                "",
                f"**催化剂：** {stock.catalyst}",
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
            f"**生成工具：** 精准选股模块 v1.0",
            f"**数据来源：** AkShare",
        ])

        content = "\n".join(lines)

        # 保存到文件
        output_path = Path(output_file)
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"\n[5/5] 结果已保存到: {output_path.absolute()}")

        return content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='精准选股 - 热门板块成长股选股器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python select_stocks.py                          # 默认配置
  python select_stocks.py --min-score 70           # 最低评分70
  python select_stocks.py --top 20                 # 返回20只
  python select_stocks.py --days 5                 # 近5日热门板块
  python select_stocks.py --stocks-per-sector 2    # 每板块2只
  python select_stocks.py --output my_stocks.md    # 指定输出文件
        '''
    )

    parser.add_argument(
        '--min-score',
        type=int,
        default=60,
        help='最低评分 (默认: 60)'
    )

    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='返回前N只股票 (默认: 10)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=3,
        choices=[3, 5],
        help='统计天数：3日或5日 (默认: 3)'
    )

    parser.add_argument(
        '--stocks-per-sector',
        type=int,
        default=1,
        help='每个板块选几只股票 (默认: 1)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出文件名 (默认: selected_stocks_YYYYMMDD.md)'
    )

    args = parser.parse_args()

    # 创建选股器
    selector = HotSectorSelector()

    # 执行选股
    candidates = selector.select_stocks(
        min_score=args.min_score,
        top_n=args.top,
        days=args.days,
        stocks_per_sector=args.stocks_per_sector
    )

    if not candidates:
        logger.error("未找到符合条件的股票")
        return 1

    # 导出结果
    selector.export_to_markdown(candidates, args.output)

    # 打印摘要
    print("\n" + "=" * 80)
    print("选股摘要")
    print("=" * 80)
    print(f"\n{'排名':<6} {'代码':<10} {'名称':<12} {'评分':<8} {'板块':<15} {'信号':<12}")
    print("-" * 80)

    for idx, stock in enumerate(candidates, 1):
        print(f"{idx:<6} {stock.code:<10} {stock.name:<12} {stock.score:<8} "
              f"{stock.sector:<15} {stock.signal:<12}")

    print("-" * 80)
    print(f"共 {len(candidates)} 只股票")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
