# -*- coding: utf-8 -*-
"""
===================================
市场环境过滤器
===================================

职责：
1. 判断大盘趋势状态（强市/弱市/震荡市）
2. 根据市场环境调整个股买入门槛
3. 提供市场环境评分和建议
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List

import pandas as pd

logger = logging.getLogger(__name__)


class MarketTrend(Enum):
    """市场趋势枚举"""
    STRONG_BULL = "强势牛市"      # 大盘强势上涨
    BULL = "牛市"                 # 大盘上涨趋势
    WEAK_BULL = "弱势牛市"        # 大盘弱势上涨
    CONSOLIDATION = "震荡市"      # 大盘震荡整理
    WEAK_BEAR = "弱势熊市"        # 大盘弱势下跌
    BEAR = "熊市"                 # 大盘下跌趋势
    STRONG_BEAR = "强势熊市"      # 大盘强势下跌


@dataclass
class MarketEnvironment:
    """市场环境数据"""
    trend: MarketTrend                    # 市场趋势
    score: int                            # 市场评分 0-100
    strength: float                       # 趋势强度 0-100

    # 大盘技术指标
    sh_index_price: float = 0.0          # 上证指数点位
    sh_index_change_pct: float = 0.0     # 上证指数涨跌幅
    sh_ma5: float = 0.0                  # 上证MA5
    sh_ma10: float = 0.0                 # 上证MA10
    sh_ma20: float = 0.0                 # 上证MA20
    sh_ma_status: str = ""               # 上证均线状态

    # 市场情绪指标
    up_down_ratio: float = 0.0           # 涨跌比（上涨家数/下跌家数）
    limit_up_count: int = 0              # 涨停家数
    limit_down_count: int = 0            # 跌停家数
    total_amount: float = 0.0            # 两市成交额（亿元）
    amount_status: str = ""              # 成交额状态

    # 调整建议
    score_adjustment: int = 0            # 个股评分调整值（-20 ~ +20）
    bias_threshold_adjustment: float = 0.0  # 乖离率阈值调整（-2% ~ +2%）
    position_suggestion: str = ""        # 仓位建议
    operation_suggestion: str = ""       # 操作建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            'trend': self.trend.value,
            'score': self.score,
            'strength': self.strength,
            'sh_index_price': self.sh_index_price,
            'sh_index_change_pct': self.sh_index_change_pct,
            'sh_ma5': self.sh_ma5,
            'sh_ma10': self.sh_ma10,
            'sh_ma20': self.sh_ma20,
            'sh_ma_status': self.sh_ma_status,
            'up_down_ratio': self.up_down_ratio,
            'limit_up_count': self.limit_up_count,
            'limit_down_count': self.limit_down_count,
            'total_amount': self.total_amount,
            'amount_status': self.amount_status,
            'score_adjustment': self.score_adjustment,
            'bias_threshold_adjustment': self.bias_threshold_adjustment,
            'position_suggestion': self.position_suggestion,
            'operation_suggestion': self.operation_suggestion,
        }


class MarketFilter:
    """
    市场环境过滤器

    功能：
    1. 分析大盘趋势（基于上证指数）
    2. 评估市场情绪（涨跌比、涨停数、成交额）
    3. 根据市场环境调整个股买入门槛
    """

    # 成交额阈值（亿元）
    AMOUNT_THRESHOLD_HIGH = 10000    # 高成交额阈值
    AMOUNT_THRESHOLD_LOW = 6000      # 低成交额阈值

    # 涨跌比阈值
    UP_DOWN_RATIO_BULL = 2.0         # 牛市涨跌比阈值
    UP_DOWN_RATIO_BEAR = 0.5         # 熊市涨跌比阈值

    def __init__(self):
        """初始化市场过滤器"""
        pass

    def analyze_market_environment(
        self,
        sh_index_df: Optional[pd.DataFrame] = None,
        market_stats: Optional[Dict[str, Any]] = None
    ) -> MarketEnvironment:
        """
        分析市场环境

        Args:
            sh_index_df: 上证指数历史数据（包含OHLCV）
            market_stats: 市场统计数据（涨跌家数、涨停数、成交额等）

        Returns:
            MarketEnvironment: 市场环境分析结果
        """
        # 初始化默认环境（震荡市）
        env = MarketEnvironment(
            trend=MarketTrend.CONSOLIDATION,
            score=50,
            strength=50.0,
        )

        # 1. 分析大盘趋势（基于上证指数）
        if sh_index_df is not None and not sh_index_df.empty:
            self._analyze_index_trend(sh_index_df, env)
        else:
            logger.warning("[市场过滤] 未提供上证指数数据，无法分析大盘趋势")

        # 2. 分析市场情绪（涨跌比、涨停数、成交额）
        if market_stats:
            self._analyze_market_sentiment(market_stats, env)
        else:
            logger.warning("[市场过滤] 未提供市场统计数据，无法分析市场情绪")

        # 3. 综合评分
        self._calculate_market_score(env)

        # 4. 生成调整建议
        self._generate_adjustment_suggestions(env)

        logger.info(f"[市场过滤] 市场环境: {env.trend.value}, 评分: {env.score}, "
                   f"个股评分调整: {env.score_adjustment:+d}, "
                   f"乖离率阈值调整: {env.bias_threshold_adjustment:+.1f}%")

        return env

    def _analyze_index_trend(self, df: pd.DataFrame, env: MarketEnvironment):
        """
        分析大盘指数趋势

        基于均线系统判断：
        - MA5 > MA10 > MA20：多头排列
        - MA5 < MA10 < MA20：空头排列
        """
        if len(df) < 20:
            logger.warning("[市场过滤] 上证指数数据不足20天，无法计算均线")
            return

        # 确保数据按日期排序
        df = df.sort_values('date').reset_index(drop=True)

        # 计算均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()

        # 获取最新数据
        latest = df.iloc[-1]
        env.sh_index_price = float(latest['close'])
        env.sh_ma5 = float(latest['MA5'])
        env.sh_ma10 = float(latest['MA10'])
        env.sh_ma20 = float(latest['MA20'])

        # 计算涨跌幅
        if len(df) >= 2:
            prev_close = df.iloc[-2]['close']
            env.sh_index_change_pct = (env.sh_index_price - prev_close) / prev_close * 100

        # 判断均线排列
        ma5, ma10, ma20 = env.sh_ma5, env.sh_ma10, env.sh_ma20

        if ma5 > ma10 > ma20:
            # 多头排列，检查间距是否扩大
            if len(df) >= 5:
                prev = df.iloc[-5]
                prev_spread = (prev['MA5'] - prev['MA20']) / prev['MA20'] * 100 if prev['MA20'] > 0 else 0
                curr_spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0

                if curr_spread > prev_spread and curr_spread > 3:
                    env.trend = MarketTrend.STRONG_BULL
                    env.sh_ma_status = "强势多头排列，均线发散上行"
                    env.strength = 90
                else:
                    env.trend = MarketTrend.BULL
                    env.sh_ma_status = "多头排列 MA5>MA10>MA20"
                    env.strength = 75
            else:
                env.trend = MarketTrend.BULL
                env.sh_ma_status = "多头排列 MA5>MA10>MA20"
                env.strength = 75

        elif ma5 > ma10 and ma10 <= ma20:
            env.trend = MarketTrend.WEAK_BULL
            env.sh_ma_status = "弱势多头，MA5>MA10 但 MA10≤MA20"
            env.strength = 55

        elif ma5 < ma10 < ma20:
            # 空头排列，检查间距是否扩大
            if len(df) >= 5:
                prev = df.iloc[-5]
                prev_spread = (prev['MA20'] - prev['MA5']) / prev['MA5'] * 100 if prev['MA5'] > 0 else 0
                curr_spread = (ma20 - ma5) / ma5 * 100 if ma5 > 0 else 0

                if curr_spread > prev_spread and curr_spread > 3:
                    env.trend = MarketTrend.STRONG_BEAR
                    env.sh_ma_status = "强势空头排列，均线发散下行"
                    env.strength = 10
                else:
                    env.trend = MarketTrend.BEAR
                    env.sh_ma_status = "空头排列 MA5<MA10<MA20"
                    env.strength = 25
            else:
                env.trend = MarketTrend.BEAR
                env.sh_ma_status = "空头排列 MA5<MA10<MA20"
                env.strength = 25

        elif ma5 < ma10 and ma10 >= ma20:
            env.trend = MarketTrend.WEAK_BEAR
            env.sh_ma_status = "弱势空头，MA5<MA10 但 MA10≥MA20"
            env.strength = 40

        else:
            env.trend = MarketTrend.CONSOLIDATION
            env.sh_ma_status = "均线缠绕，趋势不明"
            env.strength = 50

    def _analyze_market_sentiment(self, stats: Dict[str, Any], env: MarketEnvironment):
        """
        分析市场情绪

        指标：
        - 涨跌比：上涨家数/下跌家数
        - 涨停数：反映市场热度
        - 成交额：反映市场活跃度
        """
        # 涨跌家数
        up_count = stats.get('up_count', 0)
        down_count = stats.get('down_count', 0)

        if down_count > 0:
            env.up_down_ratio = up_count / down_count
        else:
            env.up_down_ratio = 10.0 if up_count > 0 else 1.0

        # 涨停跌停数
        env.limit_up_count = stats.get('limit_up_count', 0)
        env.limit_down_count = stats.get('limit_down_count', 0)

        # 成交额
        env.total_amount = stats.get('total_amount', 0.0)

        # 判断成交额状态
        if env.total_amount >= self.AMOUNT_THRESHOLD_HIGH:
            env.amount_status = "放量（成交额充足）"
        elif env.total_amount >= self.AMOUNT_THRESHOLD_LOW:
            env.amount_status = "正常（成交额适中）"
        else:
            env.amount_status = "缩量（成交额不足）"

    def _calculate_market_score(self, env: MarketEnvironment):
        """
        计算市场综合评分（0-100）

        评分维度：
        - 趋势状态（40分）
        - 涨跌比（30分）
        - 涨停数（15分）
        - 成交额（15分）
        """
        score = 0

        # 1. 趋势状态评分（40分）
        trend_scores = {
            MarketTrend.STRONG_BULL: 40,
            MarketTrend.BULL: 35,
            MarketTrend.WEAK_BULL: 28,
            MarketTrend.CONSOLIDATION: 20,
            MarketTrend.WEAK_BEAR: 12,
            MarketTrend.BEAR: 5,
            MarketTrend.STRONG_BEAR: 0,
        }
        score += trend_scores.get(env.trend, 20)

        # 2. 涨跌比评分（30分）
        if env.up_down_ratio >= 3.0:
            score += 30  # 极度强势
        elif env.up_down_ratio >= 2.0:
            score += 25  # 强势
        elif env.up_down_ratio >= 1.5:
            score += 20  # 偏强
        elif env.up_down_ratio >= 1.0:
            score += 15  # 平衡
        elif env.up_down_ratio >= 0.7:
            score += 10  # 偏弱
        elif env.up_down_ratio >= 0.5:
            score += 5   # 弱势
        else:
            score += 0   # 极度弱势

        # 3. 涨停数评分（15分）
        if env.limit_up_count >= 100:
            score += 15  # 市场热度高
        elif env.limit_up_count >= 50:
            score += 12
        elif env.limit_up_count >= 20:
            score += 9
        elif env.limit_up_count >= 10:
            score += 6
        else:
            score += 3   # 市场热度低

        # 4. 成交额评分（15分）
        if env.total_amount >= self.AMOUNT_THRESHOLD_HIGH:
            score += 15  # 成交活跃
        elif env.total_amount >= self.AMOUNT_THRESHOLD_LOW:
            score += 10  # 成交正常
        else:
            score += 5   # 成交低迷

        env.score = min(score, 100)

    def _generate_adjustment_suggestions(self, env: MarketEnvironment):
        """
        根据市场环境生成调整建议

        调整策略：
        - 强市（评分≥70）：降低门槛，放宽乖离率至7%，个股评分+10
        - 正常市（评分50-70）：保持标准，乖离率5%，个股评分不变
        - 弱市（评分<50）：提高门槛，收紧乖离率至3%，个股评分-10
        """
        score = env.score

        if score >= 75:
            # 强势牛市：大幅降低门槛
            env.score_adjustment = +15
            env.bias_threshold_adjustment = +2.0  # 乖离率放宽至7%
            env.position_suggestion = "可积极做多，建议仓位70-90%"
            env.operation_suggestion = "强势市场，可适当追涨龙头股，但仍需控制风险"

        elif score >= 60:
            # 牛市：适当降低门槛
            env.score_adjustment = +10
            env.bias_threshold_adjustment = +1.0  # 乖离率放宽至6%
            env.position_suggestion = "可积极做多，建议仓位60-80%"
            env.operation_suggestion = "市场向好，可积极参与，优选多头排列个股"

        elif score >= 50:
            # 弱势牛市/震荡市：保持标准
            env.score_adjustment = 0
            env.bias_threshold_adjustment = 0.0  # 乖离率保持5%
            env.position_suggestion = "谨慎操作，建议仓位40-60%"
            env.operation_suggestion = "市场震荡，严格按标准选股，不追高"

        elif score >= 40:
            # 弱势熊市：提高门槛
            env.score_adjustment = -10
            env.bias_threshold_adjustment = -1.0  # 乖离率收紧至4%
            env.position_suggestion = "控制仓位，建议仓位20-40%"
            env.operation_suggestion = "市场偏弱，提高买入标准，优选超跌反弹"

        else:
            # 熊市/强势熊市：大幅提高门槛
            env.score_adjustment = -15
            env.bias_threshold_adjustment = -2.0  # 乖离率收紧至3%
            env.position_suggestion = "空仓观望或轻仓，建议仓位0-20%"
            env.operation_suggestion = "市场弱势，建议空仓观望，等待趋势转强"

    def apply_market_filter(
        self,
        stock_score: int,
        market_env: MarketEnvironment
    ) -> Dict[str, Any]:
        """
        应用市场环境过滤

        根据市场环境调整个股评分和买入门槛

        Args:
            stock_score: 个股原始评分（0-100）
            market_env: 市场环境

        Returns:
            调整后的结果字典
        """
        # 调整后的评分
        adjusted_score = stock_score + market_env.score_adjustment
        adjusted_score = max(0, min(adjusted_score, 100))  # 限制在0-100

        # 调整后的乖离率阈值
        base_bias_threshold = 5.0
        adjusted_bias_threshold = base_bias_threshold + market_env.bias_threshold_adjustment
        adjusted_bias_threshold = max(3.0, min(adjusted_bias_threshold, 7.0))  # 限制在3-7%

        # 判断是否通过过滤
        passed = True
        filter_reason = ""

        # 弱市中，评分低于60分的不建议买入
        if market_env.score < 50 and adjusted_score < 60:
            passed = False
            filter_reason = f"弱市环境（市场评分{market_env.score}），个股评分{adjusted_score}未达标（需≥60）"

        # 强势熊市中，评分低于70分的不建议买入
        if market_env.trend in [MarketTrend.BEAR, MarketTrend.STRONG_BEAR] and adjusted_score < 70:
            passed = False
            filter_reason = f"{market_env.trend.value}，个股评分{adjusted_score}未达标（需≥70）"

        return {
            'original_score': stock_score,
            'adjusted_score': adjusted_score,
            'score_adjustment': market_env.score_adjustment,
            'original_bias_threshold': base_bias_threshold,
            'adjusted_bias_threshold': adjusted_bias_threshold,
            'bias_threshold_adjustment': market_env.bias_threshold_adjustment,
            'passed': passed,
            'filter_reason': filter_reason,
            'market_trend': market_env.trend.value,
            'market_score': market_env.score,
            'position_suggestion': market_env.position_suggestion,
            'operation_suggestion': market_env.operation_suggestion,
        }

    def format_market_environment(self, env: MarketEnvironment) -> str:
        """
        格式化市场环境报告

        Args:
            env: 市场环境

        Returns:
            格式化的文本报告
        """
        lines = [
            "=== 市场环境分析 ===",
            "",
            f"📊 市场趋势: {env.trend.value}",
            f"   综合评分: {env.score}/100",
            f"   趋势强度: {env.strength:.0f}/100",
            "",
            f"📈 上证指数:",
            f"   点位: {env.sh_index_price:.2f} ({env.sh_index_change_pct:+.2f}%)",
            f"   MA5:  {env.sh_ma5:.2f}",
            f"   MA10: {env.sh_ma10:.2f}",
            f"   MA20: {env.sh_ma20:.2f}",
            f"   状态: {env.sh_ma_status}",
            "",
            f"📊 市场情绪:",
            f"   涨跌比: {env.up_down_ratio:.2f}",
            f"   涨停数: {env.limit_up_count}",
            f"   跌停数: {env.limit_down_count}",
            f"   成交额: {env.total_amount:.0f}亿 ({env.amount_status})",
            "",
            f"🎯 调整建议:",
            f"   个股评分调整: {env.score_adjustment:+d}分",
            f"   乖离率阈值调整: {env.bias_threshold_adjustment:+.1f}%",
            f"   仓位建议: {env.position_suggestion}",
            f"   操作建议: {env.operation_suggestion}",
        ]

        return "\n".join(lines)


# 便捷函数
def get_market_filter() -> MarketFilter:
    """获取市场过滤器实例"""
    return MarketFilter()


if __name__ == "__main__":
    # 测试代码
    import logging
    import numpy as np
    from datetime import datetime, timedelta

    logging.basicConfig(level=logging.INFO)

    # 模拟上证指数数据（多头排列）
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
    base_price = 3000.0
    prices = [base_price]
    for i in range(29):
        change = np.random.randn() * 0.01 + 0.005  # 轻微上涨趋势
        prices.append(prices[-1] * (1 + change))

    sh_df = pd.DataFrame({
        'date': dates,
        'close': prices,
    })

    # 模拟市场统计数据（强势市场）
    market_stats = {
        'up_count': 3500,
        'down_count': 1200,
        'limit_up_count': 80,
        'limit_down_count': 5,
        'total_amount': 9500.0,
    }

    # 测试市场过滤器
    filter = MarketFilter()
    env = filter.analyze_market_environment(sh_df, market_stats)

    print(filter.format_market_environment(env))
    print("\n" + "="*50 + "\n")

    # 测试个股过滤
    stock_score = 65
    result = filter.apply_market_filter(stock_score, env)

    print(f"个股原始评分: {result['original_score']}")
    print(f"调整后评分: {result['adjusted_score']} ({result['score_adjustment']:+d})")
    print(f"乖离率阈值: {result['original_bias_threshold']:.1f}% → {result['adjusted_bias_threshold']:.1f}%")
    print(f"是否通过: {'✅ 通过' if result['passed'] else '❌ 未通过'}")
    if not result['passed']:
        print(f"原因: {result['filter_reason']}")
