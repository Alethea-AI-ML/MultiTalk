import os
import sys
import json
import tempfile
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import torch
import random
import numpy as np

# Add the parent directory to sys.path to import wan modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wan.configs import WAN_CONFIGS
import wan
from transformers import Wav2Vec2FeatureExtractor
from src.audio_analysis.wav2vec2 import Wav2Vec2Model
from wan.utils.multitalk_utils import save_video_ffmpeg
from utils import audio_prepare_single, audio_prepare_multi, get_embedding

logger = logging.getLogger(__name__)

class GradioMultiTalkPipeline:
    """Wrapper around MultiTalk pipeline for Gradio demo"""
    
    def __init__(self, ckpt_dir: str, wav2vec_dir: str, device_id: int = 0):
        """
        Initialize the MultiTalk pipeline
        
        Args:
            ckpt_dir: Path to model checkpoints
            wav2vec_dir: Path to wav2vec model
            device_id: GPU device ID
        """
        self.ckpt_dir = ckpt_dir
        self.wav2vec_dir = wav2vec_dir
        self.device_id = device_id
        self.device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
        
        # Initialize components
        self.pipeline = None
        self.wav2vec_feature_extractor = None
        self.audio_encoder = None
        self.temp_dir = tempfile.mkdtemp(prefix="multitalk_pipeline_")
        
        logger.info(f"Pipeline initialized with device: {self.device}")
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize the MultiTalk components"""
        try:
            # Validate paths
            if not os.path.exists(self.ckpt_dir):
                raise FileNotFoundError(f"Checkpoint directory not found: {self.ckpt_dir}")
            if not os.path.exists(self.wav2vec_dir):
                raise FileNotFoundError(f"Wav2Vec directory not found: {self.wav2vec_dir}")
            
            # Initialize audio encoder
            logger.info("Initializing audio encoder...")
            self.audio_encoder = Wav2Vec2Model.from_pretrained(
                self.wav2vec_dir, 
                local_files_only=True
            ).to(self.device)
            self.audio_encoder.feature_extractor._freeze_parameters()
            
            self.wav2vec_feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
                self.wav2vec_dir, 
                local_files_only=True
            )
            
            # Initialize MultiTalk pipeline
            logger.info("Initializing MultiTalk pipeline...")
            cfg = WAN_CONFIGS["multitalk-14B"]
            
            self.pipeline = wan.MultiTalkPipeline(
                config=cfg,
                checkpoint_dir=self.ckpt_dir,
                device_id=self.device_id,
                rank=0,
                t5_fsdp=False,
                dit_fsdp=False,
                use_usp=False,
                t5_cpu=False,
            )
            
            logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline components: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _prepare_audio_embeddings(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare audio embeddings from audio files"""
        try:
            # Create audio save directory
            audio_save_dir = os.path.join(
                self.temp_dir, 
                f"audio_{random.randint(1000, 9999)}"
            )
            os.makedirs(audio_save_dir, exist_ok=True)
            
            cond_audio = input_data['cond_audio']
            
            if len(cond_audio) == 2:
                # Multi-person audio
                audio_type = input_data.get('audio_type', 'add')
                
                new_human_speech1, new_human_speech2, sum_human_speechs = audio_prepare_multi(
                    cond_audio['person1'], 
                    cond_audio['person2'], 
                    audio_type
                )
                
                # Generate embeddings
                audio_embedding_1 = get_embedding(
                    new_human_speech1, 
                    self.wav2vec_feature_extractor, 
                    self.audio_encoder, 
                    device=self.device
                )
                audio_embedding_2 = get_embedding(
                    new_human_speech2, 
                    self.wav2vec_feature_extractor, 
                    self.audio_encoder, 
                    device=self.device
                )
                
                # Save embeddings and audio
                emb1_path = os.path.join(audio_save_dir, '1.pt')
                emb2_path = os.path.join(audio_save_dir, '2.pt')
                sum_audio_path = os.path.join(audio_save_dir, 'sum.wav')
                
                torch.save(audio_embedding_1, emb1_path)
                torch.save(audio_embedding_2, emb2_path)
                
                import soundfile as sf
                sf.write(sum_audio_path, sum_human_speechs, 16000)
                
                # Update input data
                input_data['cond_audio']['person1'] = emb1_path
                input_data['cond_audio']['person2'] = emb2_path
                input_data['video_audio'] = sum_audio_path
                
            elif len(cond_audio) == 1:
                # Single person audio
                human_speech = audio_prepare_single(cond_audio['person1'])
                audio_embedding = get_embedding(
                    human_speech, 
                    self.wav2vec_feature_extractor, 
                    self.audio_encoder, 
                    device=self.device
                )
                
                # Save embedding and audio
                emb_path = os.path.join(audio_save_dir, '1.pt')
                sum_audio_path = os.path.join(audio_save_dir, 'sum.wav')
                
                torch.save(audio_embedding, emb_path)
                
                import soundfile as sf
                sf.write(sum_audio_path, human_speech, 16000)
                
                # Update input data
                input_data['cond_audio']['person1'] = emb_path
                input_data['video_audio'] = sum_audio_path
            
            return input_data
            
        except Exception as e:
            logger.error(f"Audio embedding preparation failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def generate(
        self,
        input_data: Dict[str, Any],
        sampling_steps: int = 40,
        text_guide_scale: float = 5.0,
        audio_guide_scale: float = 4.0,
        frame_num: int = 81,
        seed: int = 42,
        mode: str = "single",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Optional[str]:
        """
        Generate video using MultiTalk pipeline
        
        Args:
            input_data: Input configuration dictionary
            sampling_steps: Number of sampling steps
            text_guide_scale: Text guidance scale
            audio_guide_scale: Audio guidance scale
            frame_num: Number of frames to generate
            seed: Random seed
            mode: Generation mode ("single" or "multi")
            progress_callback: Progress callback function
            
        Returns:
            Path to generated video file
        """
        try:
            if progress_callback:
                progress_callback(0.1)
            
            # Set random seed
            if seed < 0:
                seed = random.randint(0, 99999999)
            
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            np.random.seed(seed)
            random.seed(seed)
            torch.backends.cudnn.deterministic = True
            
            logger.info(f"Starting video generation with seed: {seed}")
            
            if progress_callback:
                progress_callback(0.2)
            
            # Prepare audio embeddings
            logger.info("Preparing audio embeddings...")
            processed_input_data = self._prepare_audio_embeddings(input_data.copy())
            
            if progress_callback:
                progress_callback(0.3)
            
            # Generate video
            logger.info("Generating video...")
            video_tensor = self.pipeline.generate(
                processed_input_data,
                size_buckget='multitalk-480',
                motion_frame=25,
                frame_num=frame_num,
                shift=7.0,
                sampling_steps=sampling_steps,
                text_guide_scale=text_guide_scale,
                audio_guide_scale=audio_guide_scale,
                seed=seed,
                offload_model=True,
                max_frames_num=frame_num,
                progress=False  # We handle progress externally
            )
            
            if progress_callback:
                progress_callback(0.8)
            
            if video_tensor is None:
                raise RuntimeError("Video generation returned None")
            
            # Save video
            logger.info("Saving video...")
            output_filename = f"multitalk_output_{random.randint(1000, 9999)}"
            output_path = os.path.join(self.temp_dir, f"{output_filename}.mp4")
            
            # Use the video audio if available
            audio_files = []
            if 'video_audio' in processed_input_data:
                audio_files = [processed_input_data['video_audio']]
            
            save_video_ffmpeg(video_tensor, output_filename, audio_files)
            
            # Move to temp directory if not already there
            generated_file = f"{output_filename}.mp4"
            if os.path.exists(generated_file) and not os.path.exists(output_path):
                import shutil
                shutil.move(generated_file, output_path)
            
            if progress_callback:
                progress_callback(1.0)
            
            if os.path.exists(output_path):
                logger.info(f"Video generated successfully: {output_path}")
                return output_path
            else:
                raise RuntimeError(f"Generated video file not found: {output_path}")
                
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def cleanup(self):
        """Clean up temporary files and resources"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            
            # Clear GPU memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
