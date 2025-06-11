#!/bin/bash

# MultiTalk Gradio Demo Installation Script

set -e

echo "🚀 Installing MultiTalk Gradio Demo"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Please run this script from the gradio_demo directory"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $python_version"

if [ "$(python3 -c "import sys; print(sys.version_info >= (3, 8))")" = "False" ]; then
    echo "❌ Error: Python 3.8 or higher is required"
    exit 1
fi

# Install demo requirements
echo "📦 Installing demo requirements..."
pip install -r requirements_demo.txt

# Check if main MultiTalk requirements are installed
echo "🔍 Checking main MultiTalk requirements..."
if [ -f "../requirements.txt" ]; then
    echo "📦 Installing main MultiTalk requirements..."
    pip install -r ../requirements.txt
else
    echo "⚠️  Main requirements.txt not found. Please ensure MultiTalk is properly installed."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p assets/example_images
mkdir -p assets/example_audios
mkdir -p assets/sample_outputs

# Make launch script executable
chmod +x launch.py

# Check model paths
echo "🔍 Checking model paths..."
CKPT_DIR="../weights/Wan2.1-I2V-14B-480P"
WAV2VEC_DIR="../weights/chinese-wav2vec2-base"

if [ ! -d "$CKPT_DIR" ]; then
    echo "⚠️  Checkpoint directory not found: $CKPT_DIR"
    echo "   Please download models or update MULTITALK_CKPT_DIR environment variable"
fi

if [ ! -d "$WAV2VEC_DIR" ]; then
    echo "⚠️  Wav2Vec directory not found: $WAV2VEC_DIR"
    echo "   Please download models or update MULTITALK_WAV2VEC_DIR environment variable"
fi

# Test installation
echo "🧪 Testing installation..."
python3 -c "
try:
    import gradio
    import torch
    import transformers
    import librosa
    import soundfile
    import pyloudnorm
    from PIL import Image
    print('✅ All required packages imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start the demo:"
echo "  python3 launch.py"
echo ""
echo "Or directly:"
echo "  python3 app.py"
echo ""
echo "For more options:"
echo "  python3 launch.py --help"
echo ""
echo "See README_demo.md for detailed usage instructions."
