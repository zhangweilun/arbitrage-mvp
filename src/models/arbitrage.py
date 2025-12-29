"""套利机会数据模型。"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ArbitrageOpportunity:
    """表示一个套利机会。"""
    
    token_pair: tuple[str, str]  # (token_a, token_b) 地址
    buy_dex: str
    sell_dex: str
    buy_price: float
    sell_price: float
    price_diff_pct: float
    profit_estimate: float
    liquidity: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    buy_pool_address: Optional[str] = None
    sell_pool_address: Optional[str] = None
    
    @property
    def profit_pct(self) -> float:
        """计算利润百分比。"""
        total_value = (self.profit_estimate / self.price_diff_pct * 100) if self.price_diff_pct > 0 else 0
        return (self.profit_estimate / total_value * 100) if total_value > 0 else 0.0
    
    def __str__(self) -> str:
        """字符串表示。"""
        return (
            f"ArbitrageOpportunity("
            f"pair={self.token_pair[0][:8]}.../{self.token_pair[1][:8]}..., "
            f"{self.buy_dex}→{self.sell_dex}, "
            f"diff={self.price_diff_pct:.2f}%, "
            f"profit=${self.profit_estimate:.2f})"
        )
    
    def to_dict(self) -> dict:
        """转换为字典用于日志记录/序列化。"""
        return {
            "token_pair": f"{self.token_pair[0][:8]}.../{self.token_pair[1][:8]}...",
            "buy_dex": self.buy_dex,
            "sell_dex": self.sell_dex,
            "buy_price": f"{self.buy_price:.6f}",
            "sell_price": f"{self.sell_price:.6f}",
            "price_diff_pct": f"{self.price_diff_pct:.2f}%",
            "profit_estimate": f"${self.profit_estimate:.2f}",
            "liquidity": f"${self.liquidity:.2f}",
            "timestamp": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        }


@dataclass
class ArbitrageStats:
    """套利机会的统计数据。"""
    
    total_opportunities: int = 0
    valid_opportunities: int = 0
    avg_profit: float = 0.0
    max_profit: float = 0.0
    best_opportunity: Optional[ArbitrageOpportunity] = None
    
    def update(self, opportunity: ArbitrageOpportunity, is_valid: bool):
        """Update statistics with new opportunity.
        
        Args:
            opportunity: The arbitrage opportunity
            is_valid: Whether the opportunity meets profit threshold
        """
        self.total_opportunities += 1
        
        if is_valid:
            self.valid_opportunities += 1
            
            if opportunity.profit_estimate > self.max_profit:
                self.max_profit = opportunity.profit_estimate
                self.best_opportunity = opportunity
            
            # 更新平均利润
            if self.valid_opportunities > 0:
                self.avg_profit = (
                    (self.avg_profit * (self.valid_opportunities - 1) + opportunity.profit_estimate) 
                    / self.valid_opportunities
                )
