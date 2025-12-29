"""配置管理器模块。"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict
from loguru import logger


class ConfigManager:
    """管理来自 YAML 文件的应用程序配置。"""
    
    def __init__(self, config_path: str = None):
        """初始化配置管理器。
        
        参数:
            config_path: 配置文件路径。默认为 config/config.yaml
        """
        if config_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"配置已从 {config_path} 加载")
    
    def _load_config(self) -> Dict[str, Any]:
        """从 YAML 文件加载配置。
        
        返回:
            配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"配置文件未找到: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"解析 YAML 配置错误: {e}")
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """通过点分隔的路径获取配置值。
        
        参数:
            key_path: 配置键的点分隔路径（例如，"rpc.endpoint"）
            default: 键未找到时的默认值
            
        返回:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @property
    def rpc_endpoint(self) -> str:
        """获取 Solana RPC 端点。"""
        return self.get("rpc.endpoint")

    @property
    def rpc_fallback_endpoints(self) -> list:
        """获取备用 RPC 端点。"""
        return self.get("rpc.fallback_endpoints", [])
    
    @property
    def dex_protocols(self) -> list:
        """获取要监控的 DEX 协议。"""
        return self.get("monitoring.dex_protocols", [])

    @property
    def min_liquidity(self) -> int:
        """获取最小流动性阈值。"""
        return self.get("monitoring.min_liquidity", 0)
    
    @property
    def min_profit_threshold(self) -> float:
        """获取最小利润阈值（百分比）。"""
        return self.get("monitoring.min_profit_threshold", 0.0)

    @property
    def log_level(self) -> str:
        """获取日志级别。"""
        return self.get("logging.level", "INFO")

    @property
    def log_file(self) -> str:
        """获取日志文件路径。"""
        return self.get("logging.file", "logs/arbitrage.log")


# 全局配置实例
config = ConfigManager()
