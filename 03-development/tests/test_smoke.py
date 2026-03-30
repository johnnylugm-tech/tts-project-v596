"""
Smoke tests for all modules

Basic tests to ensure all modules can be imported and basic instantiation works.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleImports:
    """Test that all modules can be imported"""
    
    def test_import_error_handler(self):
        """Test error_handler import"""
        from tts_project.error_handler import (
            TTSError, InputError, ToolError, 
            ExecutionError, SystemError, ErrorHandler
        )
        assert TTSError is not None
    
    def test_import_text_processor(self):
        """Test text_processor import"""
        from tts_project.text_processor import TextProcessor
        assert TextProcessor is not None
    
    def test_import_parameter_controller(self):
        """Test parameter_controller import"""
        from tts_project.parameter_controller import ParameterController
        assert ParameterController is not None
    
    def test_import_voice_selector(self):
        """Test voice_selector import"""
        from tts_project.voice_selector import VoiceSelector
        assert VoiceSelector is not None
    
    def test_import_synthesizer(self):
        """Test synthesizer import"""
        from tts_project.synthesizer import Synthesizer
        assert Synthesizer is not None
    
    def test_import_audio_exporter(self):
        """Test audio_exporter import"""
        from tts_project.audio_exporter import AudioExporter
        assert AudioExporter is not None
    
    def test_import_audio_merger(self):
        """Test audio_merger import"""
        from tts_project.audio_merger import AudioMerger
        assert AudioMerger is not None
    
    def test_import_tts_engine(self):
        """Test tts_engine import"""
        from tts_project.tts_engine import TTSEngine
        assert TTSEngine is not None
    
    def test_import_batch_processor(self):
        """Test batch_processor import"""
        from tts_project.batch_processor import BatchProcessor
        assert BatchProcessor is not None
    
    def test_import_cli(self):
        """Test cli import"""
        from tts_project.cli import CLIInterface
        assert CLIInterface is not None
    
    def test_import_package(self):
        """Test package import"""
        import tts_project
        assert tts_project.__version__ == "1.0.0"


class TestBasicInstantiation:
    """Test that all modules can be instantiated"""
    
    def test_instantiate_error_handler(self):
        from tts_project import ErrorHandler
        handler = ErrorHandler()
        assert handler is not None
    
    def test_instantiate_text_processor(self):
        from tts_project import TextProcessor
        processor = TextProcessor()
        assert processor is not None
    
    def test_instantiate_parameter_controller(self):
        from tts_project import ParameterController
        controller = ParameterController()
        assert controller is not None
    
    def test_instantiate_synthesizer(self):
        from tts_project import Synthesizer
        synthesizer = Synthesizer()
        assert synthesizer is not None
    
    def test_instantiate_audio_exporter(self):
        from tts_project import AudioExporter
        exporter = AudioExporter()
        assert exporter is not None
    
    def test_instantiate_audio_merger(self):
        from tts_project import AudioMerger
        merger = AudioMerger()
        assert merger is not None
    
    def test_instantiate_tts_engine(self):
        from tts_project import TTSEngine
        engine = TTSEngine()
        assert engine is not None
    
    def test_instantiate_cli(self):
        from tts_project import CLIInterface
        cli = CLIInterface()
        assert cli is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
