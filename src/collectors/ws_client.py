"""Solana RPC 的 WebSocket 客户端。"""
import asyncio
import json
import websockets
from typing import Dict, Callable, Optional, Set
from solders.pubkey import Pubkey
from loguru import logger

from src.managers.pool_manager import PoolManager
from src.utils.config import config


class SolanaWebSocketClient:
    """用于订阅 Solana 账户变更的 WebSocket 客户端。"""
    
    def __init__(self, pool_manager: PoolManager):
        """初始化 WebSocket 客户端。

        参数:
            pool_manager: 用于更新池子数据的 PoolManager 实例
        """
        self.pool_manager = pool_manager
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.rpc_endpoint = config.rpc_endpoint.replace("https://", "wss://").replace("http://", "ws://")
        self.is_connected = False
        self.subscribed_accounts: Set[str] = set()
        self.subscription_to_pool: Dict[int, str] = {}  # subscription_id -> pool_address
        self.pending_requests: Dict[int, asyncio.Future] = {}  # request_id -> Future
        self.reconnect_interval = int(config.get("websocket.reconnect_interval", 5))
        self.connection_timeout = int(config.get("websocket.connection_timeout", 30))
        self.proxy = config.get("websocket.proxy", None)  # 代理配置（可选）
        logger.info(f"reconnect_interval: {self.reconnect_interval} (type: {type(self.reconnect_interval)})")
        logger.info(f"connection_timeout: {self.connection_timeout} (type: {type(self.connection_timeout)})")
        if self.proxy:
            logger.info(f"Using proxy: {self.proxy}")
    
    async def connect(self):
        """连接到 Solana RPC WebSocket。"""
        while not self.is_connected:
            try:
                logger.info(f"Connecting to WebSocket: {self.rpc_endpoint}")
                if self.proxy:
                    logger.info(f"Using proxy: {self.proxy}")
                    connection = await asyncio.wait_for(
                        websockets.connect(self.rpc_endpoint, proxy=self.proxy),
                        timeout=self.connection_timeout
                    )
                else:
                    connection = await asyncio.wait_for(
                        websockets.connect(self.rpc_endpoint),
                        timeout=self.connection_timeout
                    )
                self.ws = connection

                # 连接成功，设置状态并重新订阅账户
                self.is_connected = True
                logger.info("WebSocket connected successfully")

                # 重新连接后重新订阅所有账户
                if self.subscribed_accounts:
                    await self._resubscribe_all()

            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                logger.info(f"Retrying in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)
    
    async def disconnect(self):
        """断开 WebSocket 连接。"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
            self.subscribed_accounts.clear()
            self.subscription_to_pool.clear()
            self.pending_requests.clear()
            logger.info("WebSocket disconnected")
    
    async def subscribe_account(self, account_pubkey: Pubkey):
        """订阅账户变更。

        参数:
            account_pubkey: 要订阅的账户公钥

        返回:
            订阅 ID
        """
        if not self.is_connected:
            await self.connect()

        account_str = str(account_pubkey)

        if account_str in self.subscribed_accounts:
            logger.debug(f"Already subscribed to account: {account_str}")
            # 查找并返回现有的 subscription_id
            for sub_id, addr in self.subscription_to_pool.items():
                if addr == account_str:
                    return sub_id
            return None

        try:
            # 生成唯一的请求 ID
            request_id = int(asyncio.get_event_loop().time() * 1000) % 1000000
            future = asyncio.Future()
            self.pending_requests[request_id] = future

            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "accountSubscribe",
                "params": [
                    account_str,
                    {
                        "encoding": "base64",
                        "commitment": "confirmed"
                    }
                ]
            }

            await self.ws.send(json.dumps(message))

            # 等待订阅响应
            try:
                response = await asyncio.wait_for(future, timeout=5.0)
                subscription_id = response.get("result")
                if subscription_id:
                    self.subscribed_accounts.add(account_str)
                    self.subscription_to_pool[subscription_id] = account_str
                    logger.info(f"Subscribed to account: {account_str[:8]}... (subscription_id={subscription_id})")
                    return subscription_id
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for subscription response: {account_str}")
            finally:
                self.pending_requests.pop(request_id, None)

        except Exception as e:
            logger.error(f"Failed to subscribe to account {account_str}: {e}")

        return None

    def _handle_response(self, data: Dict):
        """处理 JSON-RPC 响应。"""
        request_id = data.get("id")
        if request_id and request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(data)
    
    async def unsubscribe_account(self, account_pubkey: Pubkey):
        """取消订阅账户变更。

        参数:
            account_pubkey: 要取消订阅的账户公钥
        """
        account_str = str(account_pubkey)

        if account_str not in self.subscribed_accounts:
            return

        try:
            # 查找订阅 ID
            subscription_id = None
            for sub_id, addr in list(self.subscription_to_pool.items()):
                if addr == account_str:
                    subscription_id = sub_id
                    break

            if subscription_id:
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "accountUnsubscribe",
                    "params": [subscription_id]
                }

                await self.ws.send(json.dumps(message))
                self.subscribed_accounts.remove(account_str)
                self.subscription_to_pool.pop(subscription_id, None)
                logger.info(f"Unsubscribed from account: {account_str[:8]}...")

        except Exception as e:
            logger.error(f"Failed to unsubscribe from account {account_str}: {e}")
    
    async def _resubscribe_all(self):
        """重新连接后重新订阅所有账户。"""
        logger.info(f"Resubscribing to {len(self.subscribed_accounts)} accounts...")

        # 清空旧的映射，因为重新订阅会获得新的 subscription_id
        self.subscription_to_pool.clear()

        for account_str in list(self.subscribed_accounts):
            try:
                account_pubkey = Pubkey.from_string(account_str)
                await self.subscribe_account(account_pubkey)
            except Exception as e:
                logger.error(f"Failed to resubscribe to {account_str}: {e}")

        logger.info("Resubscription complete")
    
    async def listen(self, message_handler: Callable):
        """监听 WebSocket 消息。

        参数:
            message_handler: 用于处理消息的回调函数
        """
        if not self.is_connected:
            await self.connect()

        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)

                    # 首先处理响应
                    if "id" in data and data["id"] in self.pending_requests:
                        self._handle_response(data)
                    # 然后处理消息
                    elif data.get("method") == "accountNotification":
                        await message_handler(data)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed, reconnecting...")
            self.is_connected = False
            await self.connect()
            await self.listen(message_handler)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            await self.connect()
            await self.listen(message_handler)
