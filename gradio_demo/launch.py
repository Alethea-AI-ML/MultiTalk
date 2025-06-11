#!/usr/bin/env python3
"""
Simple launcher script for the MultiTalk Gradio demo
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'gradio', 'torch', 'transformers', 'librosa', 
        'soundfile', 'pyloudnorm', 'PIL'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them with:")
        print("pip install -r requirements_demo.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def check_models(ckpt_dir, wav2vec_dir):
    """Check if model files exist"""
    if not os.path.exists(ckpt_dir):
        print(f"❌ Checkpoint directory not found: {ckpt_dir}")
        return False
    
    if not os.path.exists(wav2vec_dir):
        print(f"❌ Wav2Vec directory not found: {wav2vec_dir}")
        return False
    
    # Check for key files
    key_files = [
        (ckpt_dir, 'diffusion_pytorch_model.safetensors.index.json'),
        (ckpt_dir, 'multitalk.safetensors'),
        (wav2vec_dir, 'pytorch_model.bin'),
        (wav2vec_dir, 'config.json')
    ]
    
    missing_files = []
    for directory, filename in key_files:
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            missing_files.append(filepath)
    
    if missing_files:
        print(f"❌ Missing model files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required model files found")
    return True

def check_gpu():
    """Check GPU availability"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU available: {gpu_name} ({gpu_count} device(s))")
            return True
        else:
            print("⚠️  No GPU detected - demo will run on CPU (very slow)")
            return True
    except ImportError:
        print("❌ PyTorch not installed")
        return False

def main():
    parser = argparse.ArgumentParser(description="Launch MultiTalk Gradio Demo")
    parser.add_argument("--ckpt-dir", default="../weights/Wan2.1-I2V-14B-480P", 
                       help="Path to checkpoint directory")
    parser.add_argument("--wav2vec-dir", default="../weights/chinese-wav2vec2-base",
                       help="Path to Wav2Vec model directory")
    parser.add_argument("--device-id", type=int, default=0,
                       help="GPU device ID")
    parser.add_argument("--port", type=int, default=7860,
                       help="Port to run the demo on")
    parser.add_argument("--host", default="127.0.0.1",
                       help="Host to run the demo on")
    parser.add_argument("--share", action="store_true",
                       help="Create a public link")
    parser.add_argument("--skip-checks", action="store_true",
                       help="Skip dependency and model checks")
    
    args = parser.parse_args()
    
    print("🚀 MultiTalk Gradio Demo Launcher")
    print("=" * 40)
    
    if not args.skip_checks:
        print("Checking requirements...")
        if not check_requirements():
            sys.exit(1)
        
        print("\nChecking GPU...")
        if not check_gpu():
            sys.exit(1)
        
        print("\nChecking models...")
        if not check_models(args.ckpt_dir, args.wav2vec_dir):
            print("\nModel files not found. Please ensure you have:")
            print("1. Downloaded the required models")
            print("2. Set the correct paths")
            print("\nSee README_demo.md for installation instructions")
            sys.exit(1)
    
    # Set environment variables
    os.environ['MULTITALK_CKPT_DIR'] = args.ckpt_dir
    os.environ['MULTITALK_WAV2VEC_DIR'] = args.wav2vec_dir
    os.environ['MULTITALK_DEVICE_ID'] = str(args.device_id)
    
    print(f"\n✅ All checks passed!")
    print(f"🌐 Starting demo on {args.host}:{args.port}")
    print(f"📁 Checkpoint dir: {args.ckpt_dir}")
    print(f"📁 Wav2Vec dir: {args.wav2vec_dir}")
    print(f"🎮 Device ID: {args.device_id}")
    
    if args.share:
        print("🔗 Public link will be created")
    
    print("\n" + "=" * 40)
    
    # Launch the app
    try:
        from app import main as app_main
        
        # Override launch parameters
        import app
        original_launch = app.MultiTalkGradioApp.create_interface
        
        def patched_create_interface(self):
            demo = original_launch(self)
            demo.launch(
                server_name=args.host,
                server_port=args.port,
                share=args.share
            )
            return demo
        
        app.MultiTalkGradioApp.create_interface = patched_create_interface
        app_main()
        
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Error launching demo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
