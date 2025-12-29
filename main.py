"""Solana 套利监控系统 - 主入口点"""
import asyncio
import sys
from pathlib import Path

# 导入 src.main 并在 sys.path 中添加 src 目录
from src.main import main as run_main


if __name__ == "__main__":
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\n程序正在关闭...")
