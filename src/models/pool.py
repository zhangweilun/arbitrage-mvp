"""流动性池数据模型。"""
from dataclasses import dataclass, field
from typing import Optional
from solders.pubkey import Pubkey
from datetime import datetime


@dataclass
class LiquidityPool:
    """表示 DEX 上的流动性池。"""
    
    address: Pubkey
    dex: str  # 'raydium' 或 'orca'
    token_a: Pubkey
    token_b: Pubkey
    token_a_decimals: int
    token_b_decimals: int
    reserve_a: int
    reserve_b: int
    fee_rate: float
    last_update: float = field(default_factory=lambda: datetime.now().timestamp())
    
    @property
    def price_ab(self) -> float:
        """计算代币 A 相对于代币 B 的价格。"""
        if self.reserve_a == 0:
            return 0.0
        return (self.reserve_b / 10**self.token_b_decimals) / (
            self.reserve_a / 10**self.token_a_decimals
        )
    
    @property
    def price_ba(self) -> float:
        """计算代币 B 相对于代币 A 的价格。"""
        if self.reserve_b == 0:
            return 0.0
        return (self.reserve_a / 10**self.token_a_decimals) / (
            self.reserve_b / 10**self.token_b_decimals
        )
    
    @property
    def liquidity_usd(self) -> float:
        """计算总流动性（以美元为单位，简化版）。"""
        # 这是一个简化的计算
        # 实际应用中，需要从预言机获取代币价格
        return float(self.reserve_a) + float(self.reserve_b)
    
    def update_reserves(self, reserve_a: int, reserve_b: int):
        """更新池子储备金。
        
        参数:
            reserve_a: 代币 A 的新储备金
            reserve_b: 代币 B 的新储备金
        """
        self.reserve_a = reserve_a
        self.reserve_b = reserve_b
        self.last_update = datetime.now().timestamp()
    
    def __str__(self) -> str:
        """池子的字符串表示。"""
        return (
            f"LiquidityPool({self.dex}, "
            f"{str(self.token_a)[:8]}.../{str(self.token_b)[:8]}..., "
            f"price_ab={self.price_ab:.6f}, "
            f"last_update={self.last_update})"
        )


@dataclass
class PoolPrice:
    """表示特定 DEX 上交易对的价格信息。"""
    
    dex: str
    token_pair: tuple[str, str]  # (token_a_address, token_b_address)
    price: float
    liquidity: float
    fee_rate: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    pool_address: Optional[str] = None
    
    def __str__(self) -> str:
        """字符串表示。"""
        return (
            f"PoolPrice({self.dex}, "
            f"price={self.price:.6f}, "
            f"liquidity=${self.liquidity:.2f})"
        )
