"""流动性池数据模型。"""
from dataclasses import dataclass, field
from typing import Optional
from solders.pubkey import Pubkey
from datetime import datetime
import requests



# 代币 mint 地址到 CoinGecko ID 的映射（可扩展）
TOKEN_MINT_TO_CG_ID = {
    "So11111111111111111111111111111111111111112": "solana",      # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "usd-coin",   # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "usd-coin",   # USDT (Solana)
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": "bitcoin",   # BTC (wrapped)
    # 可继续添加...
}

@dataclass
class LiquidityPool:
    """表示 DEX 上的流动性池。"""
    
    address: Pubkey  # 池子在 Solana 链上的唯一地址
    dex: str  # DEX 名称，'raydium' 或 'orca'
    token_a: Pubkey  # 代币 A 的地址（基础货币）
    token_b: Pubkey  # 代币 B 的地址（报价货币）
    token_a_decimals: int  # 代币 A 的小数位数（如 SOL 为 9）
    token_b_decimals: int  # 代币 B 的小数位数（如 USDC 为 6）
    reserve_a: int  # 池子中代币 A 的储备金数量
    reserve_b: int  # 池子中代币 B 的储备金数量
    fee_rate: float  # 交易手续费率（如 0.0025 表示 0.25%）
    last_update: float = field(default_factory=lambda: datetime.now().timestamp())  # 最后更新时间戳
    
    @property
    def price_ab(self) -> float:
        """计算代币 A 相对于代币 B 的价格。"""
        if self.reserve_a == 0:
            return 0.0
        return (self.reserve_b / 10**self.token_b_decimals) / (
            self.reserve_a / 10**self.token_a_decimals
        )
    
    @staticmethod
    def _get_price_from_coingecko(mint_str: str) -> float:
        """静态方法：根据 mint 地址获取 USD 价格"""
        cg_id = TOKEN_MINT_TO_CG_ID.get(mint_str)
        if not cg_id:
            raise ValueError(f"Unsupported token mint: {mint_str}. Add it to TOKEN_MINT_TO_CG_ID.")
        
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data[cg_id]["usd"])
        except Exception as e:
            raise RuntimeError(f"Failed to fetch price for {mint_str} ({cg_id}): {e}")

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
        """
        自动从 CoinGecko 获取代币价格，并计算池子总流动性（USD）。
        """
        # 转换为字符串（PublicKey → str）
        mint_a = str(self.token_a)
        mint_b = str(self.token_b)
        
        # # 获取价格
        # price_a = self._get_price_from_coingecko(mint_a)
        # price_b = self._get_price_from_coingecko(mint_b)
        
        # # 转换为实际数量
        # amount_a = self.reserve_a / (10 ** self.token_a_decimals)
        # amount_b = self.reserve_b / (10 ** self.token_b_decimals)
        
        # 计算总流动性
        # return amount_a * price_a + amount_b * price_b
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
    
    dex: str  # DEX 名称，'raydium' 或 'orca'
    token_pair: tuple[str, str]  # 代币对地址元组 (token_a_address, token_b_address)
    price: float  # 交易对的价格
    liquidity: float  # 池子的流动性（以美元为单位）
    fee_rate: float  # 交易手续费率（如 0.0025 表示 0.25%）
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())  # 价格记录的时间戳
    pool_address: Optional[str] = None  # 池子地址（可选）
    
    def __str__(self) -> str:
        """字符串表示。"""
        return (
            f"PoolPrice({self.dex}, "
            f"price={self.price:.6f}, "
            f"liquidity=${self.liquidity:.2f})"
        )
