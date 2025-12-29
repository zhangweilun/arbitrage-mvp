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
        self.reconnect_interval = config.get("websocket.reconnect_interval", 5)
        self.connection_timeout = config.get("websocket.connection_timeout", 30)
    
    async def connect(self):
        """连接到 Solana RPC WebSocket。"""
        while not self.is_connected:
            try:
                logger.info(f"Connecting to WebSocket: {self.rpc_endpoint}")
                self.ws = await asyncio.wait_for(
                    websockets.connect(self.rpc_endpoint),
                    timeout=self.connection_timeout
                )
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
            logger.info("WebSocket disconnected")
    
    async def subscribe_account(self, account_pubkey: Pubkey):
        """订阅账户变更。
        
        参数:
            account_pubkey: 要订阅的账户公钥
        """
        if not self.is_connected:
            await self.connect()
        
        account_str = str(account_pubkey)
        
        if account_str in self.subscribed_accounts:
            logger.debug(f"Already subscribed to account: {account_str}")
            return
        
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 1,
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
            self.subscribed_accounts.add(account_str)
            logger.info(f"Subscribed to account: {account_str[:8]}...")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to account {account_str}: {e}")
    
    async def unsubscribe_account(self, account_pubkey: Pubkey):
        """取消订阅账户变更。
        
        参数:
            account_pubkey: 要取消订阅的账户公钥
        """
        account_str = str(account_pubkey)
        
        if account_str not in self.subscribed_accounts:
            return
        
        try:
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "accountUnsubscribe",
                "params": [account_str]
            }
            
            await self.ws.send(json.dumps(message))
            self.subscribed_accounts.remove(account_str)
            logger.info(f"Unsubscribed from account: {account_str[:8]}...")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from account {account_str}: {e}")
    
    async def _resubscribe_all(self):
        """重新连接后重新订阅所有账户。"""
        logger.info(f"Resubscribing to {len(self.subscribed_accounts)} accounts...")
        
        for account_str in list(self.subscribed_accounts):
            try:
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
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
