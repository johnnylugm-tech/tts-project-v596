"""
TTS 簡報配音系統 - 主程式入口

直接執行此檔案即可啟動 CLI。
"""

import sys
from .cli import run_cli

if __name__ == "__main__":
    sys.exit(run_cli())