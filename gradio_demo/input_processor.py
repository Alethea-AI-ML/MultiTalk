import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

class InputProcessor:
    """Handles input validation and preprocessing for the Gradio demo"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="multitalk_inputs_")
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        self.supported_audio_formats = {'.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg'}
        self.max_image_size = (2048, 2048)  # Max resolution
        self.max_audio_duration = 60  # Max duration in seconds
        
    def validate_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Validate image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(image_path):
                return False, "Image file does not exist"
            
            # Check file extension
            ext = Path(image_path).suffix.lower()
            if ext not in self.supported_image_formats:
                return False, f"Unsupported image format: {ext}. Supported formats: {', '.join(self.supported_image_formats)}"
            
            # Try to open and validate image
            try:
                with Image.open(image_path) as img:
                    # Check image size
                    if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                        return False, f"Image too large. Maximum size: {self.max_image_size[0]}x{self.max_image_size[1]}"
                    
                    # Check if image has valid dimensions
                    if img.size[0] < 64 or img.size[1] < 64:
                        return False, "Image too small. Minimum size: 64x64"
                    
                    # Check if image can be converted to RGB
                    img.convert('RGB')
                    
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"
            
            return True, "Valid image"
            
        except Exception as e:
            logger.error(f"Image validation error: {e}")
            return False, f"Image validation failed: {str(e)}"
    
    def validate_audio(self, audio_path: str) -> Tuple[bool, str]:
        """
        Validate audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(audio_path):
                return False, "Audio file does not exist"
            
            # Check file extension
            ext = Path(audio_path).suffix.lower()
            if ext not in self.supported_audio_formats:
                return False, f"Unsupported audio format: {ext}. Supported formats: {', '.join(self.supported_audio_formats)}"
            
            # Try to load audio file to validate
            try:
                import librosa
                audio, sr = librosa.load(audio_path, sr=None)
                
                # Check duration
                duration = len(audio) / sr
                if duration > self.max_audio_duration:
                    return False, f"Audio too long. Maximum duration: {self.max_audio_duration} seconds"
                
                if duration < 0.5:
                    return False, "Audio too short. Minimum duration: 0.5 seconds"
                
                # Check if audio has content
                if np.max(np.abs(audio)) < 1e-6:
                    return False, "Audio appears to be silent"
                
            except Exception as e:
                return False, f"Invalid audio file: {str(e)}"
            
            return True, "Valid audio"
            
        except Exception as e:
            logger.error(f"Audio validation error: {e}")
            return False, f"Audio validation failed: {str(e)}"
    
    def process_image(self, image_path: str) -> str:
        """
        Process and prepare image for MultiTalk pipeline
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to processed image
        """
        try:
            # Validate image first
            is_valid, error_msg = self.validate_image(image_path)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Copy image to temp directory with standardized name
            processed_path = os.path.join(self.temp_dir, f"processed_image_{os.path.basename(image_path)}")
            
            # Open, process and save image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (maintain aspect ratio)
                if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                    img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                
                # Save processed image
                img.save(processed_path, 'PNG', quality=95)
            
            logger.info(f"Image processed successfully: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise ValueError(f"Image processing failed: {str(e)}")
    
    def process_single_audio(self, audio_path: str) -> str:
        """
        Process single audio file for MultiTalk pipeline
        
        Args:
            audio_path: Path to input audio
            
        Returns:
            Path to processed audio
        """
        try:
            # Validate audio first
            is_valid, error_msg = self.validate_audio(audio_path)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Copy audio to temp directory
            processed_path = os.path.join(self.temp_dir, f"processed_audio_{os.path.basename(audio_path)}")
            
            # Convert audio to standard format (16kHz WAV)
            import librosa
            import soundfile as sf
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # Normalize audio
            import pyloudnorm as pyln
            meter = pyln.Meter(16000)
            loudness = meter.integrated_loudness(audio)
            
            if abs(loudness) <= 100:  # Valid loudness measurement
                normalized_audio = pyln.normalize.loudness(audio, loudness, -23.0)
            else:
                # Fallback normalization
                normalized_audio = audio / (np.max(np.abs(audio)) + 1e-8) * 0.8
            
            # Save processed audio
            sf.write(processed_path, normalized_audio, 16000)
            
            logger.info(f"Audio processed successfully: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise ValueError(f"Audio processing failed: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up input processor temp directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Input processor cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
