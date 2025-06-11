import os
from pathlib import Path

class DemoConfig:
    """Configuration settings for the MultiTalk Gradio demo"""
    
    def __init__(self):
        # Model paths - these should be updated based on your installation
        self.CKPT_DIR = os.getenv('MULTITALK_CKPT_DIR', 'weights/Wan2.1-I2V-14B-480P')
        self.WAV2VEC_DIR = os.getenv('MULTITALK_WAV2VEC_DIR', 'weights/chinese-wav2vec2-base')
        
        # Device configuration
        self.DEVICE_ID = int(os.getenv('MULTITALK_DEVICE_ID', '0'))
        
        # Demo settings
        self.MAX_CONCURRENT_USERS = int(os.getenv('MULTITALK_MAX_USERS', '4'))
        self.MAX_QUEUE_SIZE = int(os.getenv('MULTITALK_MAX_QUEUE', '10'))
        
        # Generation defaults
        self.DEFAULT_SAMPLING_STEPS = 40
        self.DEFAULT_TEXT_GUIDE_SCALE = 5.0
        self.DEFAULT_AUDIO_GUIDE_SCALE = 4.0
        self.DEFAULT_FRAME_NUM = 81
        self.DEFAULT_SEED = 42
        
        # Limits
        self.MAX_SAMPLING_STEPS = 50
        self.MIN_SAMPLING_STEPS = 10
        self.MAX_FRAME_NUM = 201
        self.MIN_FRAME_NUM = 81
        self.MAX_GUIDE_SCALE = 10.0
        self.MIN_GUIDE_SCALE = 1.0
        
        # File size limits (in MB)
        self.MAX_IMAGE_SIZE_MB = 10
        self.MAX_AUDIO_SIZE_MB = 50
        
        # Timeout settings (in seconds)
        self.GENERATION_TIMEOUT = 300  # 5 minutes
        self.MODEL_LOAD_TIMEOUT = 120  # 2 minutes
        
        # Validate paths
        self._validate_paths()
    
    def _validate_paths(self):
        """Validate that model paths exist"""
        if not os.path.exists(self.CKPT_DIR):
            print(f"Warning: Checkpoint directory not found: {self.CKPT_DIR}")
            print("Please update MULTITALK_CKPT_DIR environment variable or ensure models are downloaded")
        
        if not os.path.exists(self.WAV2VEC_DIR):
            print(f"Warning: Wav2Vec directory not found: {self.WAV2VEC_DIR}")
            print("Please update MULTITALK_WAV2VEC_DIR environment variable or ensure models are downloaded")
    
    def get_model_info(self) -> dict:
        """Get information about model availability"""
        return {
            'ckpt_dir': self.CKPT_DIR,
            'wav2vec_dir': self.WAV2VEC_DIR,
            'ckpt_exists': os.path.exists(self.CKPT_DIR),
            'wav2vec_exists': os.path.exists(self.WAV2VEC_DIR),
            'device_id': self.DEVICE_ID
        }

# Global configuration instance
config = DemoConfig()
