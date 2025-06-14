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
from progress_capture import progress_tracker
from queue_manager import queue_manager

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
    
    def _prepare_audio_embeddings(self, input_data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
        """Prepare audio embeddings from audio files and calculate frame count"""
        try:
            # Create audio save directory
            audio_save_dir = os.path.join(
                self.temp_dir, 
                f"audio_{random.randint(1000, 9999)}"
            )
            os.makedirs(audio_save_dir, exist_ok=True)
            
            cond_audio = input_data['cond_audio']
            audio_duration = 0
            
            if len(cond_audio) == 2:
                # Multi-person audio
                audio_type = input_data.get('audio_type', 'add')
                
                new_human_speech1, new_human_speech2, sum_human_speechs = audio_prepare_multi(
                    cond_audio['person1'], 
                    cond_audio['person2'], 
                    audio_type
                )
                
                # Calculate audio duration from the combined audio
                audio_duration = len(sum_human_speechs) / 16000  # 16kHz sample rate
                
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
                
                # Calculate audio duration
                audio_duration = len(human_speech) / 16000  # 16kHz sample rate
                
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
            
            # Calculate frame count based on audio duration (25 FPS)
            calculated_frame_num = int(audio_duration * 25)
            
            # Ensure minimum frame count and reasonable maximum
            calculated_frame_num = max(25, calculated_frame_num)  # At least 1 second
            calculated_frame_num = min(calculated_frame_num, 1000)  # Max ~40 seconds
            
            # Ensure frame_num follows the 4n+1 rule required by MultiTalk
            if (calculated_frame_num - 1) % 4 != 0:
                calculated_frame_num = ((calculated_frame_num - 1) // 4 + 1) * 4 + 1
            
            # Check if audio embeddings are long enough
            # MultiTalk requires audio embedding length > frame_num
            min_required_length = calculated_frame_num + 10  # Add buffer
            
            if len(cond_audio) == 2:
                # Multi-person: check both embeddings
                if audio_embedding_1.shape[0] <= calculated_frame_num or audio_embedding_2.shape[0] <= calculated_frame_num:
                    # Reduce frame count to fit audio
                    min_audio_length = min(audio_embedding_1.shape[0], audio_embedding_2.shape[0])
                    calculated_frame_num = min(calculated_frame_num, min_audio_length - 5)
                    # Ensure 4n+1 rule
                    if (calculated_frame_num - 1) % 4 != 0:
                        calculated_frame_num = ((calculated_frame_num - 1) // 4) * 4 + 1
                    calculated_frame_num = max(25, calculated_frame_num)  # Minimum 25 frames
            else:
                # Single person: check one embedding
                if audio_embedding.shape[0] <= calculated_frame_num:
                    # Reduce frame count to fit audio
                    calculated_frame_num = min(calculated_frame_num, audio_embedding.shape[0] - 5)
                    # Ensure 4n+1 rule
                    if (calculated_frame_num - 1) % 4 != 0:
                        calculated_frame_num = ((calculated_frame_num - 1) // 4) * 4 + 1
                    calculated_frame_num = max(25, calculated_frame_num)  # Minimum 25 frames
            
            logger.info(f"Audio duration: {audio_duration:.2f}s, Calculated frames: {calculated_frame_num}")
            
            return input_data, calculated_frame_num
            
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
        progress_callback: Optional[Callable[[float], None]] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate video using MultiTalk pipeline with enhanced progress tracking
        
        Args:
            input_data: Input configuration dictionary
            sampling_steps: Number of sampling steps
            text_guide_scale: Text guidance scale
            audio_guide_scale: Audio guidance scale
            frame_num: Number of frames to generate
            seed: Random seed
            mode: Generation mode ("single" or "multi")
            progress_callback: Progress callback function
            job_id: Job ID for queue tracking
            
        Returns:
            Path to generated video file
        """
        # Create job ID if not provided
        if job_id is None:
            job_id = queue_manager.add_job(mode)
        
        # Start job tracking
        queue_manager.start_job(job_id)
        
        try:
            # Start progress capture
            with progress_tracker.start_job_tracking(job_id) as progress_capture:
                
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
                queue_manager.update_job_progress(job_id, 0.1, "Initializing generation...")
                
                if progress_callback:
                    progress_callback(0.2)
                
                # Prepare audio embeddings and calculate frame count
                logger.info("Preparing audio embeddings...")
                queue_manager.update_job_progress(job_id, 0.2, "Processing audio embeddings...")
                processed_input_data, calculated_frame_num = self._prepare_audio_embeddings(input_data.copy())
                
                # Use calculated frame number instead of the UI parameter
                actual_frame_num = calculated_frame_num
                logger.info(f"Using calculated frame count: {actual_frame_num} (ignoring UI setting: {frame_num})")
                
                if progress_callback:
                    progress_callback(0.3)
                
                # Generate video with progress tracking
                logger.info("Generating video...")
                queue_manager.update_job_progress(job_id, 0.3, f"Generating {actual_frame_num} video frames...")
                
                # Enable progress tracking in the pipeline
                video_tensor = self.pipeline.generate(
                    processed_input_data,
                    size_buckget='multitalk-480',
                    motion_frame=25,
                    frame_num=actual_frame_num,
                    shift=7.0,
                    sampling_steps=sampling_steps,
                    text_guide_scale=text_guide_scale,
                    audio_guide_scale=audio_guide_scale,
                    seed=seed,
                    offload_model=True,
                    max_frames_num=actual_frame_num,
                    progress=True  # Enable progress tracking
                )
                
                if progress_callback:
                    progress_callback(0.8)
                
                if video_tensor is None:
                    raise RuntimeError("Video generation returned None")
                
                # Save video
                logger.info("Saving video...")
                queue_manager.update_job_progress(job_id, 0.8, "Saving video file...")
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
                
                queue_manager.update_job_progress(job_id, 1.0, "Video generation complete!")
                
                if os.path.exists(output_path):
                    logger.info(f"Video generated successfully: {output_path}")
                    queue_manager.complete_job(job_id, success=True)
                    return output_path
                else:
                    raise RuntimeError(f"Generated video file not found: {output_path}")
                    
        except Exception as e:
            error_msg = f"Video generation failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            queue_manager.complete_job(job_id, success=False, error_message=str(e))
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
