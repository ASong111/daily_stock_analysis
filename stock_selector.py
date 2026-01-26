#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股工具 - 基于趋势交易策略的自动选股

功能：
1. 从全市场筛选符合条件的股票
2. 按评分排序
3. 生成自选股列表

使用方法：
    python stock_selector.py --market a  # A股选股
    python stock_selector.py --top 20    # 显示前20只
"""

import sys
import logging
from pathlib import Path
from typing import List, Tuple
import argparse

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


class StockSelector:
    """股票选股器"""

    def __init__(self):
        self.analyzer = StockTrendAnalyzer()
        self.fetcher = DataFetcherManager()

    def get_stock_list(self, market: str = 'a') -> List[str]:
        """
        获取股票列表

        Args:
            market: 市场类型 ('a': A股, 'hk': 港股, 'us': 美股)

        Returns:
            股票代码列表
        """
        try:
            import akshare as ak

            if market == 'a':
                # 获取A股列表
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    codes = df['代码'].tolist()
                    logger.info(f"获取A股列表成功，共 {len(codes)} 只")
                    return codes
            elif market == 'hk':
                # 港股列表（示例）
                logger.warning("港股选股功能待实现")
                return []
            elif market == 'us':
                # 美股列表（示例）
                logger.warning("美股选股功能待实现")
                return []

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")

        return []

    def screen_stocks(
        self,
        codes: List[str],
        min_score: int = 60,
        max_count: int = 50
    ) -> List[Tuple[str, int, str]]:
        """
        筛选股票

        Args:
            codes: 股票代码列表
            min_score: 最低评分
            max_count: 最大返回数量

        Returns:
            [(代码, 评分, 信号), ...]
        """
        results = []
        total = len(codes)

        logger.info(f"开始筛选 {total} 只股票...")
        logger.info(f"筛选条件: 评分 ≥ {min_score}")

        for idx, code in enumerate(codes, 1):
            if idx % 100 == 0:
                logger.info(f"进度: {idx}/{total} ({idx/total*100:.1f}%)")

            try:
                # 获取数据
                df, _ = self.fetcher.get_daily_data(code, days=30)

                if df is None or df.empty or len(df) < 20:
                    continue

                # 趋势分析
                result = self.analyzer.analyze(df, code)

                # 检查是否符合条件
                if result.signal_score >= min_score:
                    # 必须是多头排列
                    if result.trend_status.value in ['强势多头', '多头排列']:
                        # 乖离率必须 < 5%
                        if result.bias_ma5 < 5.0:
                            results.append((
                                code,
                                result.signal_score,
                                result.buy_signal.value,
                                result.trend_status.value,
                                result.bias_ma5
                            ))

            except Exception as e:
                logger.debug(f"[{code}] 分析失败: {e}")
                continue

        # 按评分排序
        results.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"筛选完成，共找到 {len(results)} 只符合条件的股票")

        return results[:max_count]

    def format_results(self, results: List[Tuple]) -> str:
        """
        格式化输出结果

        Args:
            results: 筛选结果

        Returns:
            格式化的文本
        """
        if not results:
            return "未找到符合条件的股票"

        lines = [
            "=" * 80,
            "选股结果",
            "=" * 80,
            "",
            f"{'排名':<6} {'代码':<10} {'评分':<8} {'信号':<12} {'趋势':<12} {'乖离率':<10}",
            "-" * 80,
        ]

        for idx, (code, score, signal, trend, bias) in enumerate(results, 1):
            lines.append(
                f"{idx:<6} {code:<10} {score:<8} {signal:<12} {trend:<12} {bias:>6.2f}%"
            )

        lines.extend([
            "-" * 80,
            f"共 {len(results)} 只股票",
            "=" * 80,
        ])

        return "\n".join(lines)

    def export_to_env(self, results: List[Tuple], output_file: str = ".env.selected"):
        """
        导出到 .env 文件格式

        Args:
            results: 筛选结果
            output_file: 输出文件路径
        """
        if not results:
            logger.warning("没有结果可导出")
            return

        codes = [code for code, _, _, _, _ in results]
        stock_list = ",".join(codes)

        content = f"""# 自动选股结果
# 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
# 共 {len(codes)} 只股票

STOCK_LIST={stock_list}
"""

        output_path = Path(output_file)
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"结果已导出到: {output_path.absolute()}")
        logger.info(f"可以将 STOCK_LIST 复制到 .env 文件中使用")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='股票选股工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python stock_selector.py                    # 默认A股选股
  python stock_selector.py --top 20           # 显示前20只
  python stock_selector.py --min-score 70     # 最低评分70
  python stock_selector.py --export           # 导出到文件
        '''
    )

    parser.add_argument(
        '--market',
        type=str,
        default='a',
        choices=['a', 'hk', 'us'],
        help='市场类型 (a: A股, hk: 港股, us: 美股)'
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
        default=30,
        help='显示前N只股票 (默认: 30)'
    )

    parser.add_argument(
        '--export',
        action='store_true',
        help='导出结果到 .env.selected 文件'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("股票选股工具")
    logger.info("=" * 80)

    # 初始化选股器
    selector = StockSelector()

    # 获取股票列表
    logger.info(f"\n[1] 获取{args.market.upper()}股票列表...")
    codes = selector.get_stock_list(args.market)

    if not codes:
        logger.error("获取股票列表失败")
        return 1

    # 筛选股票
    logger.info(f"\n[2] 开始筛选股票...")
    results = selector.screen_stocks(
        codes,
        min_score=args.min_score,
        max_count=args.top
    )

    # 显示结果
    logger.info(f"\n[3] 筛选结果:")
    print("\n" + selector.format_results(results))

    # 导出结果
    if args.export and results:
        logger.info(f"\n[4] 导出结果...")
        selector.export_to_env(results)

    logger.info("\n选股完成")

    return 0


if __name__ == "__main__":
    sys.exit(main())
