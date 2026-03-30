"""
CLI 介面模組 (CLIInterface)

命令列介面，解析使用者輸入參數並啟動合成流程。

FR 對應：FR-10
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from .tts_engine import TTSEngine
from .batch_processor import BatchProcessor
from .voice_selector import VoiceSelector
from .error_handler import ErrorHandler, TTSError


class CLIInterface:
    """
    命令列介面
    
    職責：
    - 解析命令列參數
    - 驗證輸入
    - 啟動合成流程
    - 顯示結果或錯誤
    """
    
    # 預設值
    DEFAULT_VOICE = "zh-TW-HsiaoHsiaoNeural"
    DEFAULT_RATE = "+0%"
    DEFAULT_VOLUME = "+0%"
    DEFAULT_OUTPUT = "output.mp3"
    
    def __init__(self):
        """初始化 CLI 介面"""
        self._parser = self._create_parser()
        self._args = None
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """建立命令列解析器"""
        parser = argparse.ArgumentParser(
            prog="tts-project",
            description="TTS 簡報配音系統 - 將文字轉換為語音",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
範例：
  # 基本使用
  python -m tts_project.cli --text "你好，世界"

  # 指定音色和輸出
  python -m tts_project.cli --text "你好" --voice "zh-TW-YunJheNeural" --output result.mp3

  # 調整語速和音量
  python -m tts_project.cli --text "快速朗讀" --rate "+20%" --volume "-10%"

  # 從檔案讀取文字
  python -m tts_project.cli --input text.txt --output audio.mp3

  # 列出可用音色
  python -m tts_project.cli --list-voices

  # 台灣國語音色
  python -m tts_project.cli --list-taiwan-voices
            """
        )
        
        # 輸入選項（互斥）
        input_group = parser.add_mutually_exclusive_group(required=True)
        input_group.add_argument(
            "-t", "--text",
            type=str,
            help="要轉換為語音的文字"
        )
        input_group.add_argument(
            "-i", "--input",
            type=str,
            help="包含文字的輸入檔案路徑"
        )
        
        # 音色和參數
        parser.add_argument(
            "-v", "--voice",
            type=str,
            default=self.DEFAULT_VOICE,
            help=f"音色名稱（預設：{self.DEFAULT_VOICE}）"
        )
        parser.add_argument(
            "-r", "--rate",
            type=str,
            default=self.DEFAULT_RATE,
            help="語速調整，如 +20%%, -10%%（預設：+0%%）"
        )
        parser.add_argument(
            "-V", "--volume",
            type=str,
            default=self.DEFAULT_VOLUME,
            help="音量調整，如 +20%%, -10%%（預設：+0%%）"
        )
        
        # 輸出選項
        parser.add_argument(
            "-o", "--output",
            type=str,
            default=self.DEFAULT_OUTPUT,
            help=f"輸出 MP3 檔案路徑（預設：{self.DEFAULT_OUTPUT}）"
        )
        parser.add_argument(
            "-d", "--output-dir",
            type=str,
            default=None,
            help="輸出目錄（會在 output 檔名前加上此目錄）"
        )
        
        # 資訊選項
        parser.add_argument(
            "--list-voices",
            action="store_true",
            help="列出所有可用音色"
        )
        parser.add_argument(
            "--list-taiwan-voices",
            action="store_true",
            help="列出台灣國語音色"
        )
        
        # 其他選項
        parser.add_argument(
            "-p", "--parallel",
            action="store_true",
            help="使用並行處理模式"
        )
        parser.add_argument(
            "--max-chunks",
            type=int,
            default=2,
            help="並行處理的最大 chunk 數（預設：2）"
        )
        parser.add_argument(
            "-q", "--quiet",
            action="store_true",
            help="安靜模式，僅顯示錯誤"
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="除錯模式，顯示詳細資訊"
        )
        
        return parser
    
    def parse_args(self) -> argparse.Namespace:
        """
        解析命令列參數
        
        回傳：解析後的命名空間
        
        FR 對應：FR-10
        """
        self._args = self._parser.parse_args()
        return self._args
    
    def _validate_args(self) -> None:
        """
        驗證命令列參數
        
        拋出：SystemExit（參數無效）
        """
        # 驗證 rate 格式
        import re
        rate_pattern = re.compile(r'^[-+]\d+%$')
        if not rate_pattern.match(self._args.rate):
            self._parser.error(f"無效的 rate 格式：{self._args.rate}，應為如 +20%%, -10%%")
        
        # 驗證 volume 格式
        if not rate_pattern.match(self._args.volume):
            self._parser.error(f"無效的 volume 格式：{self._args.volume}，應為如 +20%%, -10%%")
        
        # 驗證輸入檔案存在
        if self._args.input and not os.path.exists(self._args.input):
            self._parser.error(f"輸入檔案不存在：{self._args.input}")
        
        # 驗證輸出目錄可寫入
        output_dir = os.path.dirname(self._args.output)
        if output_dir and not os.access(output_dir, os.W_OK):
            if not os.path.exists(output_dir):
                # 嘗試建立目錄
                try:
                    os.makedirs(output_dir, mode=0o755, exist_ok=True)
                except OSError:
                    self._parser.error(f"無法建立輸出目錄：{output_dir}")
    
    async def _load_text(self) -> str:
        """
        載入文字內容
        
        從命令列或檔案載入文字。
        
        回傳：文字內容
        
        拋出：SystemExit（載入失敗）
        """
        if self._args.text:
            return self._args.text
        
        if self._args.input:
            try:
                with open(self._args.input, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                self._parser.error("輸入檔案編碼錯誤，請使用 UTF-8 編碼")
            except IOError as e:
                self._parser.error(f"無法讀取輸入檔案：{e}")
        
        return ""
    
    def _get_output_path(self) -> str:
        """
        取得最終輸出路徑
        
        回傳：輸出檔案路徑
        """
        if self._args.output_dir:
            return os.path.join(self._args.output_dir, os.path.basename(self._args.output))
        return self._args.output
    
    async def main(self) -> int:
        """
        主程式入口點
        
        回傳：退出碼（0=成功，非0=失敗）
        
        FR 對應：FR-10
        """
        try:
            # 解析參數
            self.parse_args()
            self._validate_args()
            
            # 處理資訊選項
            if self._args.list_voices or self._args.list_taiwan_voices:
                return await self._list_voices()
            
            # 設定日誌層級
            if self._args.debug:
                import logging
                logging.basicConfig(level=logging.DEBUG)
            elif self._args.quiet:
                import logging
                logging.basicConfig(level=logging.ERROR)
            
            # 載入文字
            text = await self._load_text()
            
            if not text or not text.strip():
                self._parser.error("文字內容為空")
            
            # 計算 chunk 數量
            from .text_processor import TextProcessor
            processor = TextProcessor()
            chunk_count = processor.get_chunk_count(text)
            
            if not self._args.quiet:
                print(f"文字長度：{len(text)} 字元")
                print(f"分段數量：{chunk_count} chunks")
                print(f"音色：{self._args.voice}")
                print(f"語速：{self._args.rate}")
                print(f"音量：{self._args.volume}")
                print()
            
            # 建立引擎
            engine = TTSEngine(
                voice=self._args.voice,
                rate=self._args.rate,
                volume=self._args.volume
            )
            
            # 執行合成
            output_path = self._get_output_path()
            
            if chunk_count == 1:
                # 單一 chunk，直接合成
                if not self._args.quiet:
                    print("正在合成...")
                
                result = await engine.synthesize_to_file(text, os.path.dirname(output_path) or ".")
                final_path = result
                
            else:
                # 多個 chunk
                if self._args.parallel:
                    if not self._args.quiet:
                        print(f"正在並行合成 {chunk_count} chunks...")
                    
                    processor = BatchProcessor(engine)
                    final_path = await processor.process_batch_parallel(
                        text=text,
                        output_path=output_path,
                        max_concurrency=self._args.max_chunks,
                        progress_callback=lambda done, total: print(f"\r進度：{done}/{total}", end="") if not self._args.quiet else None
                    )
                else:
                    if not self._args.quiet:
                        print(f"正在合成 {chunk_count} chunks...")
                    
                    final_path = await engine.synthesize_batch(text, output_path)
            
            # 完成
            if not self._args.quiet:
                print()
                print(f"完成！輸出檔案：{final_path}")
            
            # 顯示檔案大小
            file_size = os.path.getsize(final_path)
            size_kb = file_size / 1024
            print(f"檔案大小：{size_kb:.1f} KB")
            
            return 0
            
        except TTSError as e:
            print(f"錯誤：{e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n操作已取消", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"未預期錯誤：{e}", file=sys.stderr)
            if self._args.debug:
                import traceback
                traceback.print_exc()
            return 1
    
    async def _list_voices(self) -> int:
        """列出可用音色"""
        try:
            selector = VoiceSelector()
            
            if self._args.list_taiwan_voices:
                voices = await selector.list_taiwan_voices()
                print(f"台灣國語音色（共 {len(voices)} 種）：")
                print("-" * 60)
            else:
                voices = await selector.list_voices()
                print(f"所有可用音色（共 {len(voices)} 種）：")
                print("-" * 60)
            
            # 顯示音色
            for voice in voices:
                name = voice.get("Name", "")
                locale = voice.get("Locale", "")
                gender = voice.get("Gender", "")
                lang = voice.get("Language", "")
                print(f"{name:40} | {locale:10} | {gender:6} | {lang}")
            
            return 0
            
        except Exception as e:
            print(f"錯誤：{e}", file=sys.stderr)
            return 1


def run_cli() -> int:
    """
    執行 CLI
    
    回傳：退出碼
    """
    cli = CLIInterface()
    return asyncio.run(cli.main())


if __name__ == "__main__":
    sys.exit(run_cli())
