"""套利机会检测模块。"""
from typing import List, Optional
from loguru import logger

from src.models import ArbitrageOpportunity, ArbitrageStats
from src.analyzers.price import PriceAnalyzer
from src.utils.config import config
from src.utils.helpers import calculate_profit_estimate


class ArbitrageDetector:
    """检测 DEX 之间的套利机会。"""
    
    def __init__(self, price_analyzer: PriceAnalyzer):
        """初始化套利检测器。
        
        参数:
            price_analyzer: PriceAnalyzer 实例
        """
        self.price_analyzer = price_analyzer
        self.min_profit_threshold = config.min_profit_threshold
        self.min_trade_size = config.get("arbitrage.min_trade_size", 100)
        self.slippage_tolerance = config.get("arbitrage.slippage_tolerance", 0.5)
        self.stats = ArbitrageStats()
    
    def detect_opportunities(self, min_threshold: float = None) -> List[ArbitrageOpportunity]:
        """检测所有监控代币对中的套利机会。
        
        参数:
            min_threshold: 最小利润阈值（百分比）
            
        返回:
            ArbitrageOpportunity 对象列表
        """
        if min_threshold is None:
            min_threshold = self.min_profit_threshold
        
        price_diffs = self.price_analyzer.find_price_differences()
        opportunities = []
        
        for diff in price_diffs:
            # 如果价格差异低于阈值则跳过
            if diff["price_diff_pct"] < min_threshold:
                continue
            
            # 计算预估利润
            profit = calculate_profit_estimate(
                diff["buy_price"],
                diff["sell_price"],
                self.min_trade_size,
                fee_rate=0.003  # 平均费率
            )
            
            # 创建套利机会
            opportunity = ArbitrageOpportunity(
                token_pair=diff["token_pair"],
                buy_dex=diff["buy_dex"],
                sell_dex=diff["sell_dex"],
                buy_price=diff["buy_price"],
                sell_price=diff["sell_price"],
                price_diff_pct=diff["price_diff_pct"],
                profit_estimate=profit,
                liquidity=diff.get("liquidity", 0),
                buy_pool_address=diff.get("buy_pool"),
                sell_pool_address=diff.get("sell_pool")
            )
            
            opportunities.append(opportunity)
            
            # 更新统计数据
            is_valid = profit > 0
            self.stats.update(opportunity, is_valid)
        
        # 按预估利润排序（降序）
        opportunities.sort(key=lambda x: x.profit_estimate, reverse=True)
        
        return opportunities
    
    def detect_best_opportunity(self, min_threshold: float = None) -> Optional[ArbitrageOpportunity]:
        """查找最佳套利机会。
        
        参数:
            min_threshold: 最小利润阈值（百分比）
            
        返回:
            最佳 ArbitrageOpportunity 或 None
        """
        opportunities = self.detect_opportunities(min_threshold)
        return opportunities[0] if opportunities else None
    
    def print_opportunities(self, opportunities: List[ArbitrageOpportunity], limit: int = 10):
        """以格式化的方式打印套利机会。
        
        参数:
            opportunities: 机会列表
            limit: 最大显示数量
        """
        if not opportunities:
            logger.info("No arbitrage opportunities found")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 ARBITRAGE OPPORTUNITIES (Top {min(limit, len(opportunities))})")
        logger.info(f"{'='*80}")
        
        for i, opp in enumerate(opportunities[:limit], 1):
            logger.info(f"\n#{i} {opp}")
            logger.info(f"  Buy:  {opp.buy_dex} @ ${opp.buy_price:.6f}")
            logger.info(f"  Sell: {opp.sell_dex} @ ${opp.sell_price:.6f}")
            logger.info(f"  Diff: {opp.price_diff_pct:.2f}%")
            logger.info(f"  💰 Estimated Profit: ${opp.profit_estimate:.2f}")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Total opportunities: {len(opportunities)}")
        logger.info(f"{'='*80}\n")
    
    def print_stats(self):
        """打印套利统计数据。"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 ARBITRAGE STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Total opportunities detected: {self.stats.total_opportunities}")
        logger.info(f"Valid opportunities: {self.stats.valid_opportunities}")
        logger.info(f"Average profit: ${self.stats.avg_profit:.2f}")
        logger.info(f"Maximum profit: ${self.stats.max_profit:.2f}")
        
        if self.stats.best_opportunity:
            logger.info(f"\nBest opportunity:")
            logger.info(f"  {self.stats.best_opportunity}")
        
        logger.info(f"{'='*60}\n")
    
    def reset_stats(self):
        """重置套利统计数据。"""
        self.stats = ArbitrageStats()
        logger.info("Arbitrage statistics reset")
