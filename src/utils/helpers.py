"""工具函数。"""
from solders.pubkey import Pubkey
from typing import Optional
from loguru import logger


def validate_pubkey(pubkey_str: str) -> Optional[Pubkey]:
    """验证并将字符串转换为 Pubkey。
    
    参数:
        pubkey_str: 公钥字符串
        
    返回:
        如果有效返回 Pubkey 对象，否则返回 None
    """
    try:
        return Pubkey.from_string(pubkey_str)
    except Exception as e:
        logger.warning(f"无效的公钥 {pubkey_str}: {e}")
        return None


def format_amount(amount: int, decimals: int = 9) -> float:
    """将原始金额格式化为可读值。
    
    参数:
        amount: 原始金额（整数）
        decimals: 代币精度
        
    返回:
        格式化后的金额
    """
    return amount / (10 ** decimals)


def calculate_price(
    reserve_a: int, 
    reserve_b: int,
    decimals_a: int = 9,
    decimals_b: int = 9
) -> float:
    """使用恒定乘积公式从流动性储备计算价格。
    
    参数:
        reserve_a: 代币 A 的储备金
        reserve_b: 代币 B 的储备金
        decimals_a: 代币 A 的精度
        decimals_b: 代币 B 的精度
        
    返回:
        代币 A 相对于代币 B 的价格
    """
    if reserve_a == 0:
        return 0.0
    
    price = (reserve_b / 10**decimals_b) / (reserve_a / 10**decimals_a)
    return price


def calculate_price_diff(price_a: float, price_b: float) -> float:
    """计算两个价格之间的价格差异百分比。
    
    参数:
        price_a: 第一个价格
        price_b: 第二个价格
        
    返回:
        价格差异百分比
    """
    if price_a == 0 or price_b == 0:
        return 0.0
    
    diff_pct = abs(price_a - price_b) / min(price_a, price_b) * 100
    return diff_pct


def calculate_profit_estimate(
    price_a: float,
    price_b: float,
    trade_size: float,
    fee_rate: float = 0.003
) -> float:
    """计算套利交易的预估利润。
    
    参数:
        price_a: DEX A 上的价格
        price_b: DEX B 上的价格
        trade_size: 交易规模（美元）
        fee_rate: 交易费率（默认 0.3%）
        
    返回:
        预估利润（美元）
    """
    # 识别买入/卖出 DEX
    buy_price = min(price_a, price_b)
    sell_price = max(price_a, price_b)
    
    # 计算毛利润
    price_diff_pct = (sell_price - buy_price) / buy_price
    gross_profit = trade_size * price_diff_pct
    
    # 减去费用（买入费+卖出费）
    fees = trade_size * fee_rate * 2
    
    profit = gross_profit - fees
    return max(0, profit)
