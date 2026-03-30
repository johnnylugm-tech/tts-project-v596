"""
TTS 簡報配音系統

一個基於 edge-tts 的文字轉語音系統，支援批量處理和錯誤恢復。
"""

__version__ = "1.0.0"
__author__ = "TTS Project Team"

# 公開 API
from .error_handler import (
    TTSError,
    InputError,
    ToolError,
    ExecutionError,
    SystemError,
    ErrorHandler,
    CircuitBreaker,
)
from .text_processor import TextProcessor
from .parameter_controller import ParameterController
from .voice_selector import VoiceSelector
from .synthesizer import Synthesizer
from .audio_exporter import AudioExporter
from .audio_merger import AudioMerger
from .tts_engine import TTSEngine
from .batch_processor import BatchProcessor
from .cli import CLIInterface, run_cli

# 工廠函數
from .error_handler import create_error_handler
from .text_processor import create_text_processor
from .parameter_controller import create_parameter_controller
from .voice_selector import create_voice_selector
from .synthesizer import create_synthesizer
from .audio_exporter import create_audio_exporter
from .audio_merger import create_audio_merger
from .tts_engine import create_tts_engine
from .batch_processor import create_batch_processor

__all__ = [
    # 版本
    "__version__",
    # 例外
    "TTSError",
    "InputError", 
    "ToolError",
    "ExecutionError",
    "SystemError",
    # 類別
    "ErrorHandler",
    "CircuitBreaker",
    "TextProcessor",
    "ParameterController",
    "VoiceSelector",
    "Synthesizer",
    "AudioExporter",
    "AudioMerger",
    "TTSEngine",
    "BatchProcessor",
    "CLIInterface",
    # 工廠函數
    "create_error_handler",
    "create_text_processor",
    "create_parameter_controller",
    "create_voice_selector",
    "create_synthesizer",
    "create_audio_exporter",
    "create_audio_merger",
    "create_tts_engine",
    "create_batch_processor",
    # CLI
    "run_cli",
]