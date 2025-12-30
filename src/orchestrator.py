"""套利监控系统的主编排器。"""
import asyncio
import base64
from typing import Dict
from solders.pubkey import Pubkey
from loguru import logger

from src.collectors import SolanaWebSocketClient
from src.managers import PoolManager
from src.analyzers import PriceAnalyzer
from src.detectors import ArbitrageDetector
from src.models import LiquidityPool
from src.utils.config import config


class ArbitrageOrchestrator:
    """编排套利监控系统。"""
    
    def __init__(self):
        """初始化编排器。"""
        self.pool_manager = PoolManager()
        self.ws_client = SolanaWebSocketClient(self.pool_manager)
        self.price_analyzer = PriceAnalyzer(self.pool_manager)
        self.arbitrage_detector = ArbitrageDetector(self.price_analyzer)
        self.is_running = False
        
        # 示例池子地址（生产环境中会动态获取）
        self.sample_pools = {
            # Raydium 池子
            "raydium": [
                # SOL/USDC 池子
                "7ckkbzK8RNNzXiFxg5264Vjpwzi64giHZyfLKKmix1NK",
            ],
            "orca": [
                "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE",  # Orca Whirlpool SOL/USDC

            ]
        }
        
        # 代币精度
        self.token_decimals = {
            "So11111111111111111111111111111111111111112": 9,  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
        }
    
    async def initialize_sample_pools(self):
        """初始化监控的示例池子。
        
        注意：在生产环境中，您需要从 DEX API 或
        链上程序获取池子地址。这是一个简化的示例。
        """
        logger.info("正在初始化示例池子...")
        
        try:
            # SOL 代币地址
            SOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
            # USDC 代币地址
            USDC = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            
            # 创建示例池子
            for dex, addresses in self.sample_pools.items():
                for address in addresses:
                    try:
                        pool = LiquidityPool(
                            address=Pubkey.from_string(address),
                            dex=dex,
                            token_a=SOL,
                            token_b=USDC,
                            token_a_decimals=self.token_decimals.get(str(SOL), 9),
                            token_b_decimals=self.token_decimals.get(str(USDC), 6),
                            reserve_a=1000 * 10**9,  # 占位符储备金
                            reserve_b=1000 * 10**6,
                            fee_rate=0.003,  # 0.3%
                            last_update=0
                        )
                        self.pool_manager.add_pool(pool)
                    except Exception as e:
                        logger.error(f"Failed to create pool {address}: {e}")
            
            logger.info(f"已初始化 {len(self.pool_manager.get_all_pools())} 个池子")
            
        except Exception as e:
            logger.error(f"Error initializing pools: {e}")
    
    async def handle_account_update(self, data: Dict):
        """处理来自 WebSocket 的账户更新。

        参数:
            data: WebSocket 消息数据
        """
        try:
            # 解析账户更新
            if data.get("method") == "accountNotification":
                result = data.get("params", {}).get("result", {})
                account_data = result.get("value", {})
                subscription = data.get("params", {}).get("subscription")
                context = result.get("context", {})

                if not account_data:
                    return

                # 获取账户地址（从订阅信息中获取）
                # 需要根据订阅时的映射关系
                pool_address = self._find_pool_address_by_subscription(subscription)
                if not pool_address:
                    logger.debug(f"No pool found for subscription {subscription}")
                    return

                # 解码账户数据
                data_list = account_data.get("data", [])
                if not data_list or len(data_list) < 1:
                    return

                data_base64 = data_list[0]
                encoding = data_list[1] if len(data_list) > 1 else "base64"

                if data_base64:
                    try:
                        # Decode base64 data
                        data_bytes = base64.b64decode(data_base64)

                        # 根据不同的 DEX 解析储备金数据
                        pool = self.pool_manager.get_pool(Pubkey.from_string(pool_address))

                        if pool:
                            reserve_a, reserve_b = self._parse_pool_data(
                                data_bytes,
                                pool.dex
                            )

                            if reserve_a is not None and reserve_b is not None:
                                # 更新池子储备金
                                self.pool_manager.update_pool(
                                    Pubkey.from_string(pool_address),
                                    reserve_a,
                                    reserve_b
                                )
                                logger.debug(
                                    f"Updated pool {pool_address[:8]}...: "
                                    f"reserve_a={reserve_a}, reserve_b={reserve_b}"
                                )

                    except Exception as e:
                        logger.debug(f"Failed to parse account data: {e}")

        except Exception as e:
            logger.error(f"Error handling account update: {e}")

    def _find_pool_address_by_subscription(self, subscription_id: int) -> str:
        """根据订阅 ID 找到对应的池子地址。"""
        return self.ws_client.subscription_to_pool.get(subscription_id)

    def _parse_pool_data(self, data_bytes: bytes, dex: str):
        """根据 DEX 类型解析池子数据。

        参数:
            data_bytes: 解码后的字节数据
            dex: DEX 类型 ('raydium' 或 'orca')

        返回:
            (reserve_a, reserve_b) 或 (None, None) 如果解析失败
        """
        try:
            if dex == "raydium":
                return self._parse_raydium_pool(data_bytes)
            elif dex == "orca":
                return self._parse_orca_whirlpool(data_bytes)
            else:
                logger.warning(f"Unsupported DEX: {dex}")
                return None, None
        except Exception as e:
            logger.error(f"Failed to parse {dex} pool data: {e}")
            return None, None

    def _parse_raydium_pool(self, data_bytes: bytes):
        """解析 Raydium 池子数据。

        Raydium liquidity pool account layout:
        - 8 bytes: discriminator
        - 32 bytes: token_a mint
        - 32 bytes: token_b mint
        - 8 bytes: token_a reserve (u64)
        - 8 bytes: token_b reserve (u64)
        - ... other fields

        注意：这是简化版本，实际 Raydium 账户布局可能更复杂
        """
        if len(data_bytes) < 80:  # 最小长度检查
            return None, None

        import struct

        # 跳过 8 字节 discriminator 和 64 字节 token addresses (32+32)
        # reserve_a 在 offset 72 (8+64)
        reserve_a = struct.unpack("<Q", data_bytes[72:80])[0]

        # reserve_b 在 offset 80
        reserve_b = struct.unpack("<Q", data_bytes[80:88])[0]

        return reserve_a, reserve_b

    def _parse_orca_whirlpool(self, data_bytes: bytes):
        """解析 Orca Whirlpool 数据。

        Orca Whirlpool account layout:
        - 8 bytes: discriminator
        - 32 bytes: token_a mint
        - 32 bytes: token_b mint
        - 8 bytes: tick_current_index (i32)
        - 8 bytes: sqrt_price (u128)
        - 8 bytes: liquidity (u128)
        - 8 bytes: fee_rate (u16)
        - ... other fields

        注意：Whirlpool 使用不同的价格模型，这里需要转换 sqrt_price 到储备金
        """
        if len(data_bytes) < 88:
            return None, None

        import struct

        # Orca Whirlpool 使用 sqrt_price，不是直接存储储备金
        # 这里需要从 sqrt_price 和 liquidity 计算储备金
        # 简化实现，仅返回当前 liquidity 作为参考

        # 跳过 8 字节 discriminator 和 64 字节 token addresses
        # tick_current_index 在 offset 72
        tick_current_index = struct.unpack("<i", data_bytes[72:76])[0]

        # sqrt_price 在 offset 80 (u128, 占 16 字节)
        sqrt_price_low = struct.unpack("<Q", data_bytes[80:88])[0]
        sqrt_price_high = struct.unpack("<Q", data_bytes[88:96])[0]

        # liquidity 在 offset 96 (u128, 占 16 字节)
        liquidity_low = struct.unpack("<Q", data_bytes[96:104])[0]
        liquidity_high = struct.unpack("<Q", data_bytes[104:112])[0]

        # 合并 128 位值
        sqrt_price = sqrt_price_low + (sqrt_price_high << 64)
        liquidity = liquidity_low + (liquidity_high << 64)

        logger.debug(f"Orca Whirlpool: tick={tick_current_index}, "
                    f"sqrt_price={sqrt_price}, liquidity={liquidity}")

        # TODO: 实现从 sqrt_price 计算储备金的逻辑
        # 这是一个复杂的计算，涉及 tick 和价格公式
        return None, None
    
    async def monitor_prices(self):
        """监控价格并检测套利机会。"""
        while self.is_running:
            try:
                # 更新价格缓存
                self.price_analyzer.update_price_cache()
                
                # 检测套利机会
                opportunities = self.arbitrage_detector.detect_opportunities()
                
                if opportunities:
                    self.arbitrage_detector.print_opportunities(opportunities[:5])
                else:
                    logger.debug("未发现套利机会")
                
                # 等待下次检查
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in price monitoring: {e}")
                await asyncio.sleep(5)
    
    async def run(self):
        """运行套利监控系统。"""
        logger.info("🚀 正在启动套利监控系统")
        logger.info(f"RPC 端点: {config.rpc_endpoint}")
        logger.info(f"监控的 DEX: {config.dex_protocols}")
        
        try:
            # 初始化示例池子
            await self.initialize_sample_pools()
            
            # 订阅池子更新
            logger.info("正在订阅池子更新...")
            for pool in self.pool_manager.get_all_pools():
                await self.ws_client.subscribe_account(pool.address)
            
            # 开始监控
            self.is_running = True
            
            # 在后台运行价格监控
            monitor_task = asyncio.create_task(self.monitor_prices())
            
            # 监听 WebSocket 消息
            logger.info("正在监听池子更新...")
            await self.ws_client.listen(self.handle_account_update)
            
        except KeyboardInterrupt:
            logger.info("收到关闭信号")
        except Exception as e:
            logger.error(f"Error running orchestrator: {e}")
        finally:
            await self.stop()
            self.arbitrage_detector.print_stats()
    
    async def stop(self):
        """停止编排器。"""
        logger.info("正在停止套利监控...")
        self.is_running = False
        await self.ws_client.disconnect()
        logger.info("已停止")
