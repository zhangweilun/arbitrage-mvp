"""池子管理器模块 - 管理监控的流动性池。"""
from typing import Dict, List, Optional
from solders.pubkey import Pubkey
from loguru import logger

from src.models import LiquidityPool


class PoolManager:
    """管理监控的流动性池集合。"""
    
    def __init__(self):
        """初始化池子管理器。"""
        self.pools: Dict[str, LiquidityPool] = {}  # pool_address -> pool
        self.token_pair_pools: Dict[tuple, Dict[str, LiquidityPool]] = {}  # (token_a, token_b) -> {dex -> pool}
    
    def add_pool(self, pool: LiquidityPool):
        """添加池子到监控。
        
        参数:
            pool: 要添加的 LiquidityPool
        """
        pool_key = str(pool.address)
        self.pools[pool_key] = pool
        
        # 按代币对索引
        pair = self._normalize_pair(pool.token_a, pool.token_b)
        if pair not in self.token_pair_pools:
            self.token_pair_pools[pair] = {}
        self.token_pair_pools[pair][pool.dex] = pool
        
        logger.info(f"Added pool: {pool}")
    
    def get_pool(self, pool_address: Pubkey) -> Optional[LiquidityPool]:
        """根据地址获取池子。
        
        参数:
            pool_address: 池子公钥
            
        返回:
            如果找到返回 LiquidityPool，否则返回 None
        """
        return self.pools.get(str(pool_address))
    
    def get_pools_for_pair(self, token_a: Pubkey, token_b: Pubkey) -> Dict[str, LiquidityPool]:
        """获取特定代币对的所有池子。
        
        参数:
            token_a: 代币 A 地址
            token_b: 代币 B 地址
            
        返回:
            映射 DEX 名称到池子的字典
        """
        pair = self._normalize_pair(token_a, token_b)
        return self.token_pair_pools.get(pair, {})
    
    def update_pool(self, pool_address: Pubkey, reserve_a: int, reserve_b: int):
        """更新池子储备金。
        
        参数:
            pool_address: 池子公钥
            reserve_a: 代币 A 的新储备金
            reserve_b: 代币 B 的新储备金
        """
        pool = self.get_pool(pool_address)
        if pool:
            old_price = pool.price_ab
            pool.update_reserves(reserve_a, reserve_b)
            logger.debug(
                f"Updated pool {pool.dex} {pool_address[:8]}...: "
                f"price {old_price:.6f} -> {pool.price_ab:.6f}"
            )
        else:
            logger.warning(f"Pool not found: {pool_address}")
    
    def get_all_pools(self) -> List[LiquidityPool]:
        """获取所有监控的池子。
        
        返回:
            所有池子的列表
        """
        return list(self.pools.values())
    
    def get_pools_by_dex(self, dex: str) -> List[LiquidityPool]:
        """获取特定 DEX 的所有池子。
        
        参数:
            dex: DEX 名称（例如，'raydium', 'orca'）
            
        返回:
            该 DEX 的池子列表
        """
        return [pool for pool in self.pools.values() if pool.dex == dex]
    
    def _normalize_pair(self, token_a: Pubkey, token_b: Pubkey) -> tuple:
        """规范化代币对以确保一致的顺序。
        
        参数:
            token_a: 代币 A
            token_b: 代币 B
            
        返回:
            规范化的元组（按字符串表示排序）
        """
        a, b = str(token_a), str(token_b)
        return tuple(sorted([a, b]))
    
    def get_token_pairs_with_multiple_dex(self) -> List[tuple]:
        """获取在多个 DEX 上都有池子的代币对。
        
        返回:
            代币对列表
        """
        return [
            pair for pair, pools in self.token_pair_pools.items()
            if len(pools) > 1
        ]
    
    def clear(self):
        """清空所有监控的池子。"""
        self.pools.clear()
        self.token_pair_pools.clear()
        logger.info("Cleared all pools")
