import os
import logging
import traceback
import numpy as np
import torch
from typing import List, Dict, Any
from einops import rearrange
import librosa
import pyloudnorm as pyln
import subprocess

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('multitalk_demo.log')
        ]
    )

def format_error_message(error: Exception) -> str:
    """Format error message for user display"""
    error_str = str(error)
    
    # Common error patterns and user-friendly messages
    if "CUDA out of memory" in error_str:
        return "GPU memory insufficient. Try reducing frame number or using a smaller model."
    elif "FileNotFoundError" in error_str:
        return "Required model files not found. Please check model installation."
    elif "No module named" in error_str:
        return "Missing dependencies. Please install required packages."
    elif "Invalid audio" in error_str or "Audio" in error_str:
        return f"Audio processing error: {error_str}"
    elif "Invalid image" in error_str or "Image" in error_str:
        return f"Image processing error: {error_str}"
    else:
        return f"Error: {error_str}"

def get_example_data() -> Dict[str, List]:
    """Get example data for the Gradio interface"""
    
    # Check if example files exist
    examples_dir = "../examples"
    single_examples = []
    multi_examples = []
    
    try:
        # Single person examples
        if os.path.exists(f"{examples_dir}/single/single1.png"):
            single_examples.append([
                f"{examples_dir}/single/single1.png",
                f"{examples_dir}/single/1.wav",
                "A woman is passionately singing into a professional microphone in a recording studio."
            ])
        
        # Multi-person examples
        if os.path.exists(f"{examples_dir}/multi/1/multi1.png"):
            multi_examples.append([
                f"{examples_dir}/multi/1/multi1.png",
                f"{examples_dir}/multi/1/1.WAV",
                f"{examples_dir}/multi/1/2.WAV",
                "In a casual, intimate setting, a man and a woman are engaged in a heartfelt conversation inside a car."
            ])
    
    except Exception as e:
        logging.warning(f"Could not load example data: {e}")
    
    return {
        "single": single_examples,
        "multi": multi_examples
    }

def loudness_norm(audio_array: np.ndarray, sr: int = 16000, lufs: float = -23) -> np.ndarray:
    """
    Normalize audio loudness
    
    Args:
        audio_array: Input audio array
        sr: Sample rate
        lufs: Target loudness in LUFS
        
    Returns:
        Normalized audio array
    """
    try:
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(audio_array)
        if abs(loudness) > 100:
            return audio_array
        normalized_audio = pyln.normalize.loudness(audio_array, loudness, lufs)
        return normalized_audio
    except Exception as e:
        logging.warning(f"Loudness normalization failed: {e}")
        # Fallback normalization
        return audio_array / (np.max(np.abs(audio_array)) + 1e-8) * 0.8

def audio_prepare_multi(left_path: str, right_path: str, audio_type: str, sample_rate: int = 16000) -> tuple:
    """
    Prepare multi-person audio
    
    Args:
        left_path: Path to first person's audio
        right_path: Path to second person's audio  
        audio_type: Type of audio mixing ('para' or 'add')
        sample_rate: Target sample rate
        
    Returns:
        Tuple of (audio1, audio2, combined_audio)
    """
    
    if not (left_path == 'None' or right_path == 'None'):
        human_speech_array1 = audio_prepare_single(left_path)
        human_speech_array2 = audio_prepare_single(right_path)
    elif left_path == 'None':
        human_speech_array2 = audio_prepare_single(right_path)
        human_speech_array1 = np.zeros(human_speech_array2.shape[0])
    elif right_path == 'None':
        human_speech_array1 = audio_prepare_single(left_path)
        human_speech_array2 = np.zeros(human_speech_array1.shape[0])

    if audio_type == 'para':
        new_human_speech1 = human_speech_array1
        new_human_speech2 = human_speech_array2
    elif audio_type == 'add':
        new_human_speech1 = np.concatenate([
            human_speech_array1[:human_speech_array1.shape[0]], 
            np.zeros(human_speech_array2.shape[0])
        ]) 
        new_human_speech2 = np.concatenate([
            np.zeros(human_speech_array1.shape[0]), 
            human_speech_array2[:human_speech_array2.shape[0]]
        ])
    
    sum_human_speechs = new_human_speech1 + new_human_speech2
    return new_human_speech1, new_human_speech2, sum_human_speechs

def extract_audio_from_video(filename: str, sample_rate: int) -> np.ndarray:
    """
    Extract audio from video file
    
    Args:
        filename: Path to video file
        sample_rate: Target sample rate
        
    Returns:
        Audio array
    """
    raw_audio_path = filename.split('/')[-1].split('.')[0] + '.wav'
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(filename),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "2",
        str(raw_audio_path),
    ]
    subprocess.run(ffmpeg_command, check=True)
    human_speech_array, sr = librosa.load(raw_audio_path, sr=sample_rate)
    human_speech_array = loudness_norm(human_speech_array, sr)
    os.remove(raw_audio_path)
    return human_speech_array

def audio_prepare_single(audio_path: str, sample_rate: int = 16000) -> np.ndarray:
    """
    Prepare single audio file
    
    Args:
        audio_path: Path to audio file
        sample_rate: Target sample rate
        
    Returns:
        Processed audio array
    """
    ext = os.path.splitext(audio_path)[1].lower()
    if ext in ['.mp4', '.mov', '.avi', '.mkv']:
        human_speech_array = extract_audio_from_video(audio_path, sample_rate)
        return human_speech_array
    else:
        human_speech_array, sr = librosa.load(audio_path, sr=sample_rate)
        human_speech_array = loudness_norm(human_speech_array, sr)
        return human_speech_array

def get_embedding(speech_array: np.ndarray, wav2vec_feature_extractor, audio_encoder, sr: int = 16000, device: str = 'cpu') -> torch.Tensor:
    """
    Get audio embedding from speech array
    
    Args:
        speech_array: Input audio array
        wav2vec_feature_extractor: Wav2Vec feature extractor
        audio_encoder: Audio encoder model
        sr: Sample rate
        device: Device to run on
        
    Returns:
        Audio embedding tensor
    """
    audio_duration = len(speech_array) / sr
    video_length = audio_duration * 25  # Assume the video fps is 25

    # wav2vec_feature_extractor
    audio_feature = np.squeeze(
        wav2vec_feature_extractor(speech_array, sampling_rate=sr).input_values
    )
    audio_feature = torch.from_numpy(audio_feature).float().to(device=device)
    audio_feature = audio_feature.unsqueeze(0)

    # audio encoder
    with torch.no_grad():
        embeddings = audio_encoder(audio_feature, seq_len=int(video_length), output_hidden_states=True)

    if len(embeddings) == 0:
        print("Fail to extract audio embedding")
        return None

    audio_emb = torch.stack(embeddings.hidden_states[1:], dim=1).squeeze(0)
    audio_emb = rearrange(audio_emb, "b s d -> s b d")

    audio_emb = audio_emb.cpu().detach()
    return audio_emb

def check_dependencies() -> Dict[str, bool]:
    """
    Check if all required dependencies are available
    
    Returns:
        Dictionary of dependency status
    """
    dependencies = {
        'torch': False,
        'gradio': False,
        'librosa': False,
        'PIL': False,
        'transformers': False,
        'soundfile': False,
        'pyloudnorm': False,
        'ffmpeg': False
    }
    
    try:
        import torch
        dependencies['torch'] = True
    except ImportError:
        pass
    
    try:
        import gradio
        dependencies['gradio'] = True
    except ImportError:
        pass
    
    try:
        import librosa
        dependencies['librosa'] = True
    except ImportError:
        pass
    
    try:
        from PIL import Image
        dependencies['PIL'] = True
    except ImportError:
        pass
    
    try:
        import transformers
        dependencies['transformers'] = True
    except ImportError:
        pass
    
    try:
        import soundfile
        dependencies['soundfile'] = True
    except ImportError:
        pass
    
    try:
        import pyloudnorm
        dependencies['pyloudnorm'] = True
    except ImportError:
        pass
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        dependencies['ffmpeg'] = result.returncode == 0
    except FileNotFoundError:
        pass
    
    return dependencies

def validate_model_paths(ckpt_dir: str, wav2vec_dir: str) -> Dict[str, bool]:
    """
    Validate that required model paths exist
    
    Args:
        ckpt_dir: Checkpoint directory path
        wav2vec_dir: Wav2Vec model directory path
        
    Returns:
        Dictionary of path validation status
    """
    validation = {
        'ckpt_dir_exists': os.path.exists(ckpt_dir),
        'wav2vec_dir_exists': os.path.exists(wav2vec_dir),
        'diffusion_model_exists': False,
        'vae_model_exists': False,
        'wav2vec_model_exists': False
    }
    
    if validation['ckpt_dir_exists']:
        # Check for key model files
        diffusion_files = [
            'diffusion_pytorch_model.safetensors.index.json',
            'multitalk.safetensors'
        ]
        validation['diffusion_model_exists'] = all(
            os.path.exists(os.path.join(ckpt_dir, f)) for f in diffusion_files
        )
        
        vae_files = ['vae_pytorch_model.bin']
        validation['vae_model_exists'] = any(
            os.path.exists(os.path.join(ckpt_dir, f)) for f in vae_files
        )
    
    if validation['wav2vec_dir_exists']:
        wav2vec_files = ['pytorch_model.bin', 'config.json']
        validation['wav2vec_model_exists'] = all(
            os.path.exists(os.path.join(wav2vec_dir, f)) for f in wav2vec_files
        )
    
    return validation
