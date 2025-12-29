"""价格分析模块。"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from src.models import LiquidityPool, PoolPrice
from src.managers.pool_manager import PoolManager
from src.utils.config import config


class PriceAnalyzer:
    """分析池子数据并计算价格。"""
    
    def __init__(self, pool_manager: PoolManager):
        """初始化价格分析器。
        
        参数:
            pool_manager: PoolManager 实例
        """
        self.pool_manager = pool_manager
        self.price_cache: Dict[tuple, Dict[str, PoolPrice]] = {}  # (token_a, token_b) -> {dex -> PoolPrice}
        self.min_profit_threshold = config.min_profit_threshold
    
    def calculate_pool_price(self, pool: LiquidityPool) -> PoolPrice:
        """从池子数据计算价格。
        
        参数:
            pool: LiquidityPool
            
        返回:
            PoolPrice 对象
        """
        price = pool.price_ab
        liquidity = pool.liquidity_usd
        
        return PoolPrice(
            dex=pool.dex,
            token_pair=(str(pool.token_a), str(pool.token_b)),
            price=price,
            liquidity=liquidity,
            fee_rate=pool.fee_rate,
            timestamp=pool.last_update,
            pool_address=str(pool.address)
        )
    
    def update_price_cache(self):
        """使用最新的池子数据更新价格缓存。"""
        for pool in self.pool_manager.get_all_pools():
            pool_price = self.calculate_pool_price(pool)
            pair_key = pool_price.token_pair
            
            if pair_key not in self.price_cache:
                self.price_cache[pair_key] = {}
            
            self.price_cache[pair_key][pool.dex] = pool_price
    
    def get_price(self, token_a: str, token_b: str, dex: str) -> Optional[PoolPrice]:
        """获取特定 DEX 上交易对的当前价格。
        
        参数:
            token_a: 代币 A 地址
            token_b: 代币 B 地址
            dex: DEX 名称
            
        返回:
            如果找到返回 PoolPrice，否则返回 None
        """
        pair = self._normalize_pair(token_a, token_b)
        return self.price_cache.get(pair, {}).get(dex)
    
    def get_prices_for_pair(self, token_a: str, token_b: str) -> Dict[str, PoolPrice]:
        """获取交易对在所有 DEX 上的所有价格。
        
        参数:
            token_a: 代币 A 地址
            token_b: 代币 B 地址
            
        返回:
            映射 DEX 到 PoolPrice 的字典
        """
        pair = self._normalize_pair(token_a, token_b)
        return self.price_cache.get(pair, {})
    
    def find_price_differences(self) -> List[Dict]:
        """查找所有监控交易对在 DEX 之间的价格差异。
        
        返回:
            价格差异信息列表
        """
        price_diffs = []
        
        for pair_key, dex_prices in self.price_cache.items():
            if len(dex_prices) < 2:
                continue  # 至少需要 2 个 DEX 才能进行套利
            
            token_a, token_b = pair_key
            
            # 获取所有价格
            prices = [
                {"dex": dex, "price": price.price, "pool_address": price.pool_address}
                for dex, price in dex_prices.items()
            ]
            
            if len(prices) < 2:
                continue
            
            # 查找最低和最高价格
            min_price_info = min(prices, key=lambda x: x["price"])
            max_price_info = max(prices, key=lambda x: x["price"])
            
            # 计算价格差异
            price_diff_pct = (
                (max_price_info["price"] - min_price_info["price"]) 
                / min_price_info["price"] * 100
            ) if min_price_info["price"] > 0 else 0
            
            if price_diff_pct > 0:
                price_diffs.append({
                    "token_pair": pair_key,
                    "buy_dex": min_price_info["dex"],
                    "sell_dex": max_price_info["dex"],
                    "buy_price": min_price_info["price"],
                    "sell_price": max_price_info["price"],
                    "buy_pool": min_price_info["pool_address"],
                    "sell_pool": max_price_info["pool_address"],
                    "price_diff_pct": price_diff_pct,
                    "num_dex": len(prices)
                })
        
        # 按价格差异排序（降序）
        price_diffs.sort(key=lambda x: x["price_diff_pct"], reverse=True)
        
        return price_diffs
    
    def get_highest_price_diff(self, min_threshold: float = None) -> Optional[Dict]:
        """Get the highest price difference opportunity.
        
        Args:
            min_threshold: Minimum price difference threshold (%)
            
        Returns:
            Price difference info or None
        """
        if min_threshold is None:
            min_threshold = self.min_profit_threshold
        
        price_diffs = self.find_price_differences()
        
        for diff in price_diffs:
            if diff["price_diff_pct"] >= min_threshold:
                return diff
        
        return None
    
    def get_average_price(self, token_a: str, token_b: str) -> Optional[float]:
        """计算所有 DEX 上的平均价格。
        
        参数:
            token_a: 代币 A 地址
            token_b: 代币 B 地址
            
        返回:
            平均价格或 None
        """
        prices = self.get_prices_for_pair(token_a, token_b)
        
        if not prices:
            return None
        
        total = sum(p.price for p in prices.values())
        return total / len(prices)
    
    def _normalize_pair(self, token_a: str, token_b: str) -> tuple:
        """规范化代币对以保持一致的顺序。
        
        参数:
            token_a: 代币 A 地址
            token_b: 代币 B 地址
            
        返回:
            规范化的元组
        """
        return tuple(sorted([token_a, token_b]))
    
    def clear_cache(self):
        """清空价格缓存。"""
        self.price_cache.clear()
        logger.info("Price cache cleared")
