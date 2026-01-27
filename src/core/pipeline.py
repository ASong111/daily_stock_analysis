# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - 核心分析流水线
===================================

职责：
1. 管理整个分析流程
2. 协调数据获取、存储、搜索、分析、通知等模块
3. 实现并发控制和异常处理
4. 提供股票分析的核心功能
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import List, Dict, Any, Optional, Tuple

from src.config import get_config, Config
from src.storage import get_db
from data_provider import DataFetcherManager
from data_provider.realtime_types import ChipDistribution
from src.analyzer import ClaudeAnalyzer, GeminiAnalyzer, AnalysisResult, STOCK_NAME_MAP
from src.notification import NotificationService, NotificationChannel
from src.search_service import SearchService
from src.enums import ReportType
from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult
from src.market_filter import MarketFilter, MarketEnvironment
from bot.models import BotMessage


logger = logging.getLogger(__name__)


class StockAnalysisPipeline:
    """
    股票分析主流程调度器
    
    职责：
    1. 管理整个分析流程
    2. 协调数据获取、存储、搜索、分析、通知等模块
    3. 实现并发控制和异常处理
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        max_workers: Optional[int] = None,
        source_message: Optional[BotMessage] = None
    ):
        """
        初始化调度器
        
        Args:
            config: 配置对象（可选，默认使用全局配置）
            max_workers: 最大并发线程数（可选，默认从配置读取）
        """
        self.config = config or get_config()
        self.max_workers = max_workers or self.config.max_workers
        self.source_message = source_message
        
        # 初始化各模块
        self.db = get_db()
        self.fetcher_manager = DataFetcherManager()
        # 不再单独创建 akshare_fetcher，统一使用 fetcher_manager 获取增强数据
        self.trend_analyzer = StockTrendAnalyzer()  # 趋势分析器
        self.market_filter = MarketFilter()  # 市场环境过滤器

        # 智能选择 AI 分析器（优先级：Claude > Gemini）
        self.analyzer = self._init_analyzer()

        self.notifier = NotificationService(source_message=source_message)

        # 初始化搜索服务
        self.search_service = SearchService(
            bocha_keys=self.config.bocha_api_keys,
            tavily_keys=self.config.tavily_api_keys,
            serpapi_keys=self.config.serpapi_keys,
        )

        # 市场环境缓存（避免重复分析）
        self.market_environment: Optional[MarketEnvironment] = None
        
        logger.info(f"调度器初始化完成，最大并发数: {self.max_workers}")
        logger.info("已启用趋势分析器 (MA5>MA10>MA20 多头判断)")
        logger.info("已启用市场环境过滤器 (大盘趋势判断)")
        # 打印实时行情/筹码配置状态
        if self.config.enable_realtime_quote:
            logger.info(f"实时行情已启用 (优先级: {self.config.realtime_source_priority})")
        else:
            logger.info("实时行情已禁用，将使用历史收盘价")
        if self.config.enable_chip_distribution:
            logger.info("筹码分布分析已启用")
        else:
            logger.info("筹码分布分析已禁用")
        if self.search_service.is_available:
            logger.info("搜索服务已启用 (Tavily/SerpAPI)")
        else:
            logger.warning("搜索服务未启用（未配置 API Key）")

    def _init_analyzer(self):
        """
        智能初始化 AI 分析器

        优先级策略：Claude > Gemini > OpenAI
        - 如果配置了 Claude API Key，使用 Claude
        - 否则如果配置了 Gemini API Key，使用 Gemini
        - 否则如果配置了 OpenAI API Key，使用 OpenAI
        - 都没配置则返回 None（仅技术分析）

        Returns:
            AI 分析器实例或 None
        """
        from src.analyzer import ClaudeAnalyzer, GeminiAnalyzer

        # 优先使用 Claude
        if self.config.claude_api_key:
            logger.info("✅ 使用 Claude AI 分析器")
            logger.info(f"   模型: {self.config.claude_model}")
            if self.config.claude_base_url:
                logger.info(f"   API 端点: {self.config.claude_base_url}")
            return ClaudeAnalyzer(
                api_key=self.config.claude_api_key,
                model=self.config.claude_model,
                base_url=self.config.claude_base_url
            )

        # 降级到 Gemini
        elif self.config.gemini_api_key:
            logger.info("✅ 使用 Gemini AI 分析器")
            logger.info(f"   模型: {self.config.gemini_model}")
            return GeminiAnalyzer(api_key=self.config.gemini_api_key)

        # 降级到 OpenAI
        elif self.config.openai_api_key:
            logger.info("✅ 使用 OpenAI 兼容分析器")
            logger.info(f"   模型: {self.config.openai_model}")
            if self.config.openai_base_url:
                logger.info(f"   API 端点: {self.config.openai_base_url}")
            # 注意：需要实现 OpenAIAnalyzer 类
            logger.warning("⚠️  OpenAIAnalyzer 尚未实现，将使用 Gemini")
            return GeminiAnalyzer(api_key=self.config.gemini_api_key) if self.config.gemini_api_key else None

        # 都没配置
        else:
            logger.warning("⚠️  未配置任何 AI API Key，将仅进行技术分析")
            return None

    def fetch_and_save_stock_data(
        self, 
        code: str,
        force_refresh: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        获取并保存单只股票数据
        
        断点续传逻辑：
        1. 检查数据库是否已有今日数据
        2. 如果有且不强制刷新，则跳过网络请求
        3. 否则从数据源获取并保存
        
        Args:
            code: 股票代码
            force_refresh: 是否强制刷新（忽略本地缓存）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            today = date.today()
            
            # 断点续传检查：如果今日数据已存在，跳过
            if not force_refresh and self.db.has_today_data(code, today):
                logger.info(f"[{code}] 今日数据已存在，跳过获取（断点续传）")
                return True, None
            
            # 从数据源获取数据
            logger.info(f"[{code}] 开始从数据源获取数据...")
            df, source_name = self.fetcher_manager.get_daily_data(code, days=30)
            
            if df is None or df.empty:
                return False, "获取数据为空"
            
            # 保存到数据库
            saved_count = self.db.save_daily_data(df, code, source_name)
            logger.info(f"[{code}] 数据保存成功（来源: {source_name}，新增 {saved_count} 条）")
            
            return True, None
            
        except Exception as e:
            error_msg = f"获取/保存数据失败: {str(e)}"
            logger.error(f"[{code}] {error_msg}")
            return False, error_msg

    def get_market_environment(self) -> Optional[MarketEnvironment]:
        """
        获取市场环境（带缓存）

        分析大盘趋势，用于调整个股买入门槛

        Returns:
            MarketEnvironment 或 None
        """
        # 如果已有缓存，直接返回
        if self.market_environment is not None:
            return self.market_environment

        try:
            logger.info("[市场过滤] 开始分析市场环境...")

            # 1. 获取上证指数历史数据
            sh_index_df = None
            try:
                sh_index_df, _ = self.fetcher_manager.get_daily_data('sh000001', days=30)
                if sh_index_df is not None and not sh_index_df.empty:
                    logger.info(f"[市场过滤] 获取上证指数数据成功，共 {len(sh_index_df)} 条")
                else:
                    logger.warning("[市场过滤] 上证指数数据为空")
            except Exception as e:
                logger.warning(f"[市场过滤] 获取上证指数数据失败: {e}")

            # 2. 获取市场统计数据
            market_stats = None
            try:
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    change_col = '涨跌幅'
                    amount_col = '成交额'

                    if change_col in df.columns:
                        import pandas as pd
                        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
                        up_count = len(df[df[change_col] > 0])
                        down_count = len(df[df[change_col] < 0])
                        limit_up_count = len(df[df[change_col] >= 9.9])
                        limit_down_count = len(df[df[change_col] <= -9.9])

                        # 成交额
                        total_amount = 0.0
                        if amount_col in df.columns:
                            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
                            total_amount = df[amount_col].sum() / 1e8  # 转为亿元

                        market_stats = {
                            'up_count': up_count,
                            'down_count': down_count,
                            'limit_up_count': limit_up_count,
                            'limit_down_count': limit_down_count,
                            'total_amount': total_amount,
                        }
                        logger.info(f"[市场过滤] 市场统计: 涨{up_count} 跌{down_count} "
                                  f"涨停{limit_up_count} 跌停{limit_down_count} "
                                  f"成交额{total_amount:.0f}亿")
            except Exception as e:
                logger.warning(f"[市场过滤] 获取市场统计数据失败: {e}")

            # 3. 分析市场环境
            env = self.market_filter.analyze_market_environment(sh_index_df, market_stats)

            # 缓存结果
            self.market_environment = env

            # 打印市场环境报告
            logger.info("\n" + self.market_filter.format_market_environment(env))

            return env

        except Exception as e:
            logger.error(f"[市场过滤] 分析市场环境失败: {e}")
            return None

    def analyze_stock(self, code: str, market_env: Optional[MarketEnvironment] = None) -> Optional[AnalysisResult]:
        """
        分析单只股票（增强版：含量比、换手率、筹码分析、多维度情报、市场环境过滤）

        流程：
        1. 获取实时行情（量比、换手率）- 通过 DataFetcherManager 自动故障切换
        2. 获取筹码分布 - 通过 DataFetcherManager 带熔断保护
        3. 进行趋势分析（基于交易理念）
        4. 多维度情报搜索（最新消息+风险排查+业绩预期）
        5. 从数据库获取分析上下文
        6. 应用市场环境过滤（调整评分和乖离率阈值）
        7. 调用 AI 进行综合分析

        Args:
            code: 股票代码
            market_env: 市场环境（可选，如果不提供则自动获取）

        Returns:
            AnalysisResult 或 None（如果分析失败）
        """
        try:
            # 获取股票名称（优先从实时行情获取真实名称）
            stock_name = STOCK_NAME_MAP.get(code, '')
            
            # Step 1: 获取实时行情（量比、换手率等）- 使用统一入口，自动故障切换
            realtime_quote = None
            try:
                realtime_quote = self.fetcher_manager.get_realtime_quote(code)
                if realtime_quote:
                    # 使用实时行情返回的真实股票名称
                    if realtime_quote.name:
                        stock_name = realtime_quote.name
                    # 兼容不同数据源的字段（有些数据源可能没有 volume_ratio）
                    volume_ratio = getattr(realtime_quote, 'volume_ratio', None)
                    turnover_rate = getattr(realtime_quote, 'turnover_rate', None)
                    logger.info(f"[{code}] {stock_name} 实时行情: 价格={realtime_quote.price}, "
                              f"量比={volume_ratio}, 换手率={turnover_rate}% "
                              f"(来源: {realtime_quote.source.value if hasattr(realtime_quote, 'source') else 'unknown'})")
                else:
                    logger.info(f"[{code}] 实时行情获取失败或已禁用，将使用历史数据进行分析")
            except Exception as e:
                logger.warning(f"[{code}] 获取实时行情失败: {e}")
            
            # 如果还是没有名称，使用代码作为名称
            if not stock_name:
                stock_name = f'股票{code}'
            
            # Step 2: 获取筹码分布 - 使用统一入口，带熔断保护
            chip_data = None
            try:
                chip_data = self.fetcher_manager.get_chip_distribution(code)
                if chip_data:
                    logger.info(f"[{code}] 筹码分布: 获利比例={chip_data.profit_ratio:.1%}, "
                              f"90%集中度={chip_data.concentration_90:.2%}")
                else:
                    logger.debug(f"[{code}] 筹码分布获取失败或已禁用")
            except Exception as e:
                logger.warning(f"[{code}] 获取筹码分布失败: {e}")
            
            # Step 3: 趋势分析（基于交易理念）
            trend_result: Optional[TrendAnalysisResult] = None
            try:
                # 获取历史数据进行趋势分析
                context = self.db.get_analysis_context(code)
                if context and 'raw_data' in context:
                    import pandas as pd
                    raw_data = context['raw_data']
                    if isinstance(raw_data, list) and len(raw_data) > 0:
                        df = pd.DataFrame(raw_data)
                        trend_result = self.trend_analyzer.analyze(df, code)
                        logger.info(f"[{code}] 趋势分析: {trend_result.trend_status.value}, "
                                  f"买入信号={trend_result.buy_signal.value}, 评分={trend_result.signal_score}")
            except Exception as e:
                logger.warning(f"[{code}] 趋势分析失败: {e}")
            
            # Step 4: 多维度情报搜索（最新消息+风险排查+业绩预期）
            news_context = None
            if self.search_service.is_available:
                logger.info(f"[{code}] 开始多维度情报搜索...")
                
                # 使用多维度搜索（最多3次搜索）
                intel_results = self.search_service.search_comprehensive_intel(
                    stock_code=code,
                    stock_name=stock_name,
                    max_searches=3
                )
                
                # 格式化情报报告
                if intel_results:
                    news_context = self.search_service.format_intel_report(intel_results, stock_name)
                    total_results = sum(
                        len(r.results) for r in intel_results.values() if r.success
                    )
                    logger.info(f"[{code}] 情报搜索完成: 共 {total_results} 条结果")
                    logger.debug(f"[{code}] 情报搜索结果:\n{news_context}")
            else:
                logger.info(f"[{code}] 搜索服务不可用，跳过情报搜索")
            
            # Step 5: 获取分析上下文（技术面数据）
            context = self.db.get_analysis_context(code)
            
            if context is None:
                logger.warning(f"[{code}] 无法获取历史行情数据，将仅基于新闻和实时行情分析")
                from datetime import date
                context = {
                    'code': code,
                    'stock_name': stock_name,
                    'date': date.today().isoformat(),
                    'data_missing': True,
                    'today': {},
                    'yesterday': {}
                }
            
            # Step 6: 增强上下文数据（添加实时行情、筹码、趋势分析结果、股票名称）
            enhanced_context = self._enhance_context(
                context,
                realtime_quote,
                chip_data,
                trend_result,
                stock_name  # 传入股票名称
            )

            # Step 7: 应用市场环境过滤（调整评分和乖离率阈值）
            if market_env is None:
                market_env = self.get_market_environment()

            if market_env and trend_result:
                # 应用市场过滤
                filter_result = self.market_filter.apply_market_filter(
                    trend_result.signal_score,
                    market_env
                )

                # 将市场环境信息添加到上下文
                enhanced_context['market_environment'] = {
                    'trend': market_env.trend.value,
                    'score': market_env.score,
                    'sh_ma_status': market_env.sh_ma_status,
                    'up_down_ratio': market_env.up_down_ratio,
                    'score_adjustment': filter_result['score_adjustment'],
                    'adjusted_bias_threshold': filter_result['adjusted_bias_threshold'],
                    'position_suggestion': filter_result['position_suggestion'],
                    'operation_suggestion': filter_result['operation_suggestion'],
                }

                # 记录过滤结果
                logger.info(f"[{code}] 市场过滤: {market_env.trend.value}(评分{market_env.score}), "
                          f"个股评分 {filter_result['original_score']} → {filter_result['adjusted_score']} "
                          f"({filter_result['score_adjustment']:+d}), "
                          f"乖离率阈值 {filter_result['original_bias_threshold']:.1f}% → "
                          f"{filter_result['adjusted_bias_threshold']:.1f}%")

                # 如果未通过过滤，记录原因
                if not filter_result['passed']:
                    logger.warning(f"[{code}] 未通过市场过滤: {filter_result['filter_reason']}")

            # Step 8: 调用 AI 分析（传入增强的上下文和新闻）
            result = self.analyzer.analyze(enhanced_context, news_context=news_context)
            
            return result
            
        except Exception as e:
            logger.error(f"[{code}] 分析失败: {e}")
            logger.exception(f"[{code}] 详细错误信息:")
            return None
    
    def _enhance_context(
        self,
        context: Dict[str, Any],
        realtime_quote,
        chip_data: Optional[ChipDistribution],
        trend_result: Optional[TrendAnalysisResult],
        stock_name: str = ""
    ) -> Dict[str, Any]:
        """
        增强分析上下文
        
        将实时行情、筹码分布、趋势分析结果、股票名称添加到上下文中
        
        Args:
            context: 原始上下文
            realtime_quote: 实时行情数据（UnifiedRealtimeQuote 或 None）
            chip_data: 筹码分布数据
            trend_result: 趋势分析结果
            stock_name: 股票名称
            
        Returns:
            增强后的上下文
        """
        enhanced = context.copy()
        
        # 添加股票名称
        if stock_name:
            enhanced['stock_name'] = stock_name
        elif realtime_quote and getattr(realtime_quote, 'name', None):
            enhanced['stock_name'] = realtime_quote.name
        
        # 添加实时行情（兼容不同数据源的字段差异）
        if realtime_quote:
            # 使用 getattr 安全获取字段，缺失字段返回 None 或默认值
            volume_ratio = getattr(realtime_quote, 'volume_ratio', None)
            enhanced['realtime'] = {
                'name': getattr(realtime_quote, 'name', ''),
                'price': getattr(realtime_quote, 'price', None),
                'volume_ratio': volume_ratio,
                'volume_ratio_desc': self._describe_volume_ratio(volume_ratio) if volume_ratio else '无数据',
                'turnover_rate': getattr(realtime_quote, 'turnover_rate', None),
                'pe_ratio': getattr(realtime_quote, 'pe_ratio', None),
                'pb_ratio': getattr(realtime_quote, 'pb_ratio', None),
                'total_mv': getattr(realtime_quote, 'total_mv', None),
                'circ_mv': getattr(realtime_quote, 'circ_mv', None),
                'change_60d': getattr(realtime_quote, 'change_60d', None),
                'source': getattr(realtime_quote, 'source', None),
            }
            # 移除 None 值以减少上下文大小
            enhanced['realtime'] = {k: v for k, v in enhanced['realtime'].items() if v is not None}
        
        # 添加筹码分布
        if chip_data:
            current_price = getattr(realtime_quote, 'price', 0) if realtime_quote else 0
            enhanced['chip'] = {
                'profit_ratio': chip_data.profit_ratio,
                'avg_cost': chip_data.avg_cost,
                'concentration_90': chip_data.concentration_90,
                'concentration_70': chip_data.concentration_70,
                'chip_status': chip_data.get_chip_status(current_price or 0),
            }
        
        # 添加趋势分析结果
        if trend_result:
            enhanced['trend_analysis'] = {
                'trend_status': trend_result.trend_status.value,
                'ma_alignment': trend_result.ma_alignment,
                'trend_strength': trend_result.trend_strength,
                'bias_ma5': trend_result.bias_ma5,
                'bias_ma10': trend_result.bias_ma10,
                'volume_status': trend_result.volume_status.value,
                'volume_trend': trend_result.volume_trend,
                'buy_signal': trend_result.buy_signal.value,
                'signal_score': trend_result.signal_score,
                'signal_reasons': trend_result.signal_reasons,
                'risk_factors': trend_result.risk_factors,
            }
        
        return enhanced
    
    def _describe_volume_ratio(self, volume_ratio: float) -> str:
        """
        量比描述
        
        量比 = 当前成交量 / 过去5日平均成交量
        """
        if volume_ratio < 0.5:
            return "极度萎缩"
        elif volume_ratio < 0.8:
            return "明显萎缩"
        elif volume_ratio < 1.2:
            return "正常"
        elif volume_ratio < 2.0:
            return "温和放量"
        elif volume_ratio < 3.0:
            return "明显放量"
        else:
            return "巨量"
    
    def process_single_stock(
        self,
        code: str,
        skip_analysis: bool = False,
        single_stock_notify: bool = False,
        report_type: ReportType = ReportType.SIMPLE,
        market_env: Optional[MarketEnvironment] = None
    ) -> Optional[AnalysisResult]:
        """
        处理单只股票的完整流程

        包括：
        1. 获取数据
        2. 保存数据
        3. AI 分析（含市场环境过滤）
        4. 单股推送（可选，#55）

        此方法会被线程池调用，需要处理好异常

        Args:
            code: 股票代码
            skip_analysis: 是否跳过 AI 分析
            single_stock_notify: 是否启用单股推送模式（每分析完一只立即推送）
            report_type: 报告类型枚举（从配置读取，Issue #119）
            market_env: 市场环境（可选）

        Returns:
            AnalysisResult 或 None
        """
        logger.info(f"========== 开始处理 {code} ==========")
        
        try:
            # Step 1: 获取并保存数据
            success, error = self.fetch_and_save_stock_data(code)
            
            if not success:
                logger.warning(f"[{code}] 数据获取失败: {error}")
                # 即使获取失败，也尝试用已有数据分析
            
            # Step 2: AI 分析
            if skip_analysis:
                logger.info(f"[{code}] 跳过 AI 分析（dry-run 模式）")
                return None

            result = self.analyze_stock(code, market_env=market_env)
            
            if result:
                logger.info(
                    f"[{code}] 分析完成: {result.operation_advice}, "
                    f"评分 {result.sentiment_score}"
                )
                
                # 单股推送模式（#55）：每分析完一只股票立即推送
                if single_stock_notify and self.notifier.is_available():
                    try:
                        # 根据报告类型选择生成方法
                        if report_type == ReportType.FULL:
                            # 完整报告：使用决策仪表盘格式
                            report_content = self.notifier.generate_dashboard_report([result])
                            logger.info(f"[{code}] 使用完整报告格式")
                        else:
                            # 精简报告：使用单股报告格式（默认）
                            report_content = self.notifier.generate_single_stock_report(result)
                            logger.info(f"[{code}] 使用精简报告格式")
                        
                        if self.notifier.send(report_content):
                            logger.info(f"[{code}] 单股推送成功")
                        else:
                            logger.warning(f"[{code}] 单股推送失败")
                    except Exception as e:
                        logger.error(f"[{code}] 单股推送异常: {e}")
            
            return result
            
        except Exception as e:
            # 捕获所有异常，确保单股失败不影响整体
            logger.exception(f"[{code}] 处理过程发生未知异常: {e}")
            return None
    
    def run(
        self, 
        stock_codes: Optional[List[str]] = None,
        dry_run: bool = False,
        send_notification: bool = True
    ) -> List[AnalysisResult]:
        """
        运行完整的分析流程
        
        流程：
        1. 获取待分析的股票列表
        2. 使用线程池并发处理
        3. 收集分析结果
        4. 发送通知
        
        Args:
            stock_codes: 股票代码列表（可选，默认使用配置中的自选股）
            dry_run: 是否仅获取数据不分析
            send_notification: 是否发送推送通知
            
        Returns:
            分析结果列表
        """
        start_time = time.time()
        
        # 使用配置中的股票列表
        if stock_codes is None:
            self.config.refresh_stock_list()
            stock_codes = self.config.stock_list
        
        if not stock_codes:
            logger.error("未配置自选股列表，请在 .env 文件中设置 STOCK_LIST")
            return []
        
        logger.info(f"===== 开始分析 {len(stock_codes)} 只股票 =====")
        logger.info(f"股票列表: {', '.join(stock_codes)}")
        logger.info(f"并发数: {self.max_workers}, 模式: {'仅获取数据' if dry_run else '完整分析'}")

        # === 获取市场环境（在分析个股前）===
        market_env = None
        if not dry_run:
            market_env = self.get_market_environment()
            if market_env:
                logger.info(f"[市场环境] {market_env.trend.value}, 评分: {market_env.score}/100")
                logger.info(f"[市场环境] {market_env.operation_suggestion}")
            else:
                logger.warning("[市场环境] 获取失败，将使用默认标准")

        # === 批量预取实时行情（优化：避免每只股票都触发全量拉取）===
        # 只有股票数量 >= 5 时才进行预取，少量股票直接逐个查询更高效
        if len(stock_codes) >= 5:
            prefetch_count = self.fetcher_manager.prefetch_realtime_quotes(stock_codes)
            if prefetch_count > 0:
                logger.info(f"已启用批量预取架构：一次拉取全市场数据，{len(stock_codes)} 只股票共享缓存")
        
        # 单股推送模式（#55）：从配置读取
        single_stock_notify = getattr(self.config, 'single_stock_notify', False)
        # Issue #119: 从配置读取报告类型
        report_type_str = getattr(self.config, 'report_type', 'simple').lower()
        report_type = ReportType.FULL if report_type_str == 'full' else ReportType.SIMPLE
        # Issue #128: 从配置读取分析间隔
        analysis_delay = getattr(self.config, 'analysis_delay', 0)

        if single_stock_notify:
            logger.info(f"已启用单股推送模式：每分析完一只股票立即推送（报告类型: {report_type_str}）")
        
        results: List[AnalysisResult] = []
        
        # 使用线程池并发处理
        # 注意：max_workers 设置较低（默认3）以避免触发反爬
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_code = {
                executor.submit(
                    self.process_single_stock,
                    code,
                    skip_analysis=dry_run,
                    single_stock_notify=single_stock_notify and send_notification,
                    report_type=report_type,  # Issue #119: 传递报告类型
                    market_env=market_env  # 传递市场环境
                ): code
                for code in stock_codes
            }
            
            # 收集结果
            for idx, future in enumerate(as_completed(future_to_code)):
                code = future_to_code[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)

                    # Issue #128: 分析间隔 - 在个股分析和大盘分析之间添加延迟
                    if idx < len(stock_codes) - 1 and analysis_delay > 0:
                        logger.debug(f"等待 {analysis_delay} 秒后继续下一只股票...")
                        time.sleep(analysis_delay)

                except Exception as e:
                    logger.error(f"[{code}] 任务执行失败: {e}")
        
        # 统计
        elapsed_time = time.time() - start_time
        
        # dry-run 模式下，数据获取成功即视为成功
        if dry_run:
            # 检查哪些股票的数据今天已存在
            success_count = sum(1 for code in stock_codes if self.db.has_today_data(code))
            fail_count = len(stock_codes) - success_count
        else:
            success_count = len(results)
            fail_count = len(stock_codes) - success_count
        
        logger.info("===== 分析完成 =====")
        logger.info(f"成功: {success_count}, 失败: {fail_count}, 耗时: {elapsed_time:.2f} 秒")
        
        # 发送通知（单股推送模式下跳过汇总推送，避免重复）
        if results and send_notification and not dry_run:
            if single_stock_notify:
                # 单股推送模式：只保存汇总报告，不再重复推送
                logger.info("单股推送模式：跳过汇总推送，仅保存报告到本地")
                self._send_notifications(results, skip_push=True)
            else:
                self._send_notifications(results)
        
        return results
    
    def _send_notifications(self, results: List[AnalysisResult], skip_push: bool = False) -> None:
        """
        发送分析结果通知
        
        生成决策仪表盘格式的报告
        
        Args:
            results: 分析结果列表
            skip_push: 是否跳过推送（仅保存到本地，用于单股推送模式）
        """
        try:
            logger.info("生成决策仪表盘日报...")
            
            # 生成决策仪表盘格式的详细日报
            report = self.notifier.generate_dashboard_report(results)
            
            # 保存到本地
            filepath = self.notifier.save_report_to_file(report)
            logger.info(f"决策仪表盘日报已保存: {filepath}")
            
            # 跳过推送（单股推送模式）
            if skip_push:
                return
            
            # 推送通知
            if self.notifier.is_available():
                channels = self.notifier.get_available_channels()
                context_success = self.notifier.send_to_context(report)

                # 企业微信：只发精简版（平台限制）
                wechat_success = False
                if NotificationChannel.WECHAT in channels:
                    dashboard_content = self.notifier.generate_wechat_dashboard(results)
                    logger.info(f"企业微信仪表盘长度: {len(dashboard_content)} 字符")
                    logger.debug(f"企业微信推送内容:\n{dashboard_content}")
                    wechat_success = self.notifier.send_to_wechat(dashboard_content)

                # 其他渠道：发完整报告（避免自定义 Webhook 被 wechat 截断逻辑污染）
                non_wechat_success = False
                for channel in channels:
                    if channel == NotificationChannel.WECHAT:
                        continue
                    if channel == NotificationChannel.FEISHU:
                        non_wechat_success = self.notifier.send_to_feishu(report) or non_wechat_success
                    elif channel == NotificationChannel.TELEGRAM:
                        non_wechat_success = self.notifier.send_to_telegram(report) or non_wechat_success
                    elif channel == NotificationChannel.EMAIL:
                        non_wechat_success = self.notifier.send_to_email(report) or non_wechat_success
                    elif channel == NotificationChannel.CUSTOM:
                        non_wechat_success = self.notifier.send_to_custom(report) or non_wechat_success
                    else:
                        logger.warning(f"未知通知渠道: {channel}")

                success = wechat_success or non_wechat_success or context_success
                if success:
                    logger.info("决策仪表盘推送成功")
                else:
                    logger.warning("决策仪表盘推送失败")
            else:
                logger.info("通知渠道未配置，跳过推送")
                
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
