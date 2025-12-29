"""套利监控系统的主入口点。"""
import asyncio
from loguru import logger

from .orchestrator import ArbitrageOrchestrator
from .utils.config import config


def setup_logging():
    """配置日志记录。"""
    # 移除默认处理程序
    logger.remove()
    
    # 添加自定义格式的控制台处理程序
    logger.add(
        sink=lambda msg: print(msg, end=''),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=config.log_level
    )
    
    # 添加文件处理程序
    logger.add(
        sink=config.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=config.log_level,
        rotation=config.get("logging.max_size", "10 MB"),
        retention=config.get("logging.backup_count", 5)
    )
    
    logger.info(f"日志已初始化: {config.log_level}")


async def main():
    """主异步函数。"""
    # 设置日志记录
    setup_logging()
    
    # 创建并运行编排器
    orchestrator = ArbitrageOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("正在关闭...")
