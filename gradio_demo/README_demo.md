# MultiTalk Gradio Demo

A production-ready Gradio web interface for the MultiTalk audio-driven multi-person conversational video generation system.

## Features

- 🎬 **Interactive Web Interface**: User-friendly Gradio interface with real-time progress tracking
- 👤 **Single Person Mode**: Generate videos with one person speaking/singing
- 👥 **Multi-Person Mode**: Generate conversations between two people with synchronized lip movements
- ⚙️ **Advanced Controls**: Fine-tune generation parameters for optimal results
- 📚 **Built-in Examples**: Pre-loaded examples to get started quickly
- 🔧 **Production Ready**: Error handling, input validation, and resource management
- 🎯 **Smart Defaults**: Automatic parameter optimization based on inputs

## Installation

### Prerequisites

1. **Install MultiTalk**: Follow the main installation instructions in the parent directory
2. **Download Models**: Ensure you have downloaded the required model weights
3. **GPU Requirements**: NVIDIA GPU with at least 8GB VRAM recommended

### Setup Demo Environment

```bash
# Navigate to demo directory
cd gradio_demo

# Install additional demo dependencies
pip install -r requirements_demo.txt

# Set environment variables (optional)
export MULTITALK_CKPT_DIR="../weights/Wan2.1-I2V-14B-480P"
export MULTITALK_WAV2VEC_DIR="../weights/chinese-wav2vec2-base"
export MULTITALK_DEVICE_ID="0"
```

## Quick Start

### Basic Usage

```bash
# Run the demo
python app.py
```

The demo will be available at `http://localhost:7860`

### Configuration

You can configure the demo using environment variables:

```bash
# Model paths
export MULTITALK_CKPT_DIR="/path/to/your/checkpoints"
export MULTITALK_WAV2VEC_DIR="/path/to/wav2vec/model"

# Performance settings
export MULTITALK_DEVICE_ID="0"  # GPU device ID
export MULTITALK_MAX_USERS="4"  # Max concurrent users
export MULTITALK_MAX_QUEUE="10" # Max queue size

# Run with custom settings
python app.py
```

## Usage Guide

### Single Person Generation

1. **Upload Reference Image**: Choose a clear image of a person
2. **Upload Audio File**: Provide speech or singing audio (WAV, MP3, etc.)
3. **Write Description**: Describe the scene and setting
4. **Adjust Settings** (optional): Modify advanced parameters
5. **Generate**: Click "Generate Video" and wait for results

### Multi-Person Generation

1. **Upload Reference Image**: Choose an image with two people
2. **Upload Audio Files**: Provide separate audio for each person
3. **Select Audio Mode**:
   - **Sequential (add)**: People speak one after another
   - **Parallel (para)**: People speak simultaneously
4. **Set Bounding Boxes** (optional): Define person locations
5. **Write Description**: Describe the conversation scene
6. **Generate**: Click "Generate Video"

### Advanced Settings

- **Sampling Steps** (10-50): Higher values = better quality, slower generation
- **Text Guidance Scale** (1-10): How closely to follow the text prompt
- **Audio Guidance Scale** (1-10): How closely to follow the audio
- **Frame Number** (81-201): Video length (81 frames ≈ 3.2 seconds at 25fps)
- **Seed**: For reproducible results

## Input Requirements

### Images
- **Formats**: JPG, PNG, BMP, TIFF, WebP
- **Size**: 64x64 to 2048x2048 pixels
- **Content**: Clear view of person(s), good lighting
- **Quality**: High resolution recommended for best results

### Audio
- **Formats**: WAV, MP3, M4A, FLAC, AAC, OGG
- **Duration**: 0.5 to 60 seconds
- **Quality**: Clear speech, minimal background noise
- **Sample Rate**: Any (automatically converted to 16kHz)

## Tips for Best Results

### Image Selection
- Use high-quality, well-lit images
- Ensure faces are clearly visible
- Avoid extreme angles or occlusions
- For multi-person: both people should be visible

### Audio Quality
- Use clear, high-quality audio recordings
- Minimize background noise
- Ensure consistent volume levels
- For multi-person: similar audio quality for both speakers

### Prompt Writing
- Be descriptive about the scene and setting
- Include details about lighting, mood, and environment
- Mention specific actions or expressions
- Keep prompts focused and clear

### Parameter Tuning
- **For better lip sync**: Increase audio guidance scale (4-6)
- **For better prompt following**: Increase text guidance scale (5-7)
- **For faster generation**: Reduce sampling steps (20-30)
- **For higher quality**: Increase sampling steps (40-50)

## Troubleshooting

### Common Issues

**"GPU memory insufficient"**
- Reduce frame number
- Close other GPU applications
- Use smaller batch sizes

**"Model files not found"**
- Check model paths in config
- Ensure models are downloaded correctly
- Verify file permissions

**"Audio processing failed"**
- Check audio file format
- Ensure audio is not corrupted
- Try converting to WAV format

**"Generation takes too long"**
- Reduce sampling steps
- Use shorter audio clips
- Check GPU utilization

### Performance Optimization

1. **GPU Memory**: Monitor VRAM usage, reduce frame count if needed
2. **Generation Speed**: Lower sampling steps for faster results
3. **Quality vs Speed**: Balance parameters based on requirements
4. **Concurrent Users**: Limit simultaneous generations

## API Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MULTITALK_CKPT_DIR` | `weights/Wan2.1-I2V-14B-480P` | Path to model checkpoints |
| `MULTITALK_WAV2VEC_DIR` | `weights/chinese-wav2vec2-base` | Path to Wav2Vec model |
| `MULTITALK_DEVICE_ID` | `0` | GPU device ID |
| `MULTITALK_MAX_USERS` | `4` | Maximum concurrent users |
| `MULTITALK_MAX_QUEUE` | `10` | Maximum queue size |

### File Structure

```
gradio_demo/
├── app.py                 # Main Gradio application
├── demo_pipeline.py       # MultiTalk pipeline wrapper
├── input_processor.py     # Input validation and processing
├── utils.py              # Utility functions
├── config.py             # Configuration settings
├── requirements_demo.txt  # Demo dependencies
└── README_demo.md        # This file
```

## Development

### Adding New Features

1. **Custom Models**: Modify `config.py` to support additional models
2. **New Input Types**: Extend `input_processor.py` for new formats
3. **UI Improvements**: Update `app.py` for interface changes
4. **Pipeline Extensions**: Modify `demo_pipeline.py` for new capabilities

### Testing

```bash
# Test individual components
python -c "from utils import check_dependencies; print(check_dependencies())"
python -c "from config import config; print(config.get_model_info())"

# Test pipeline initialization
python -c "from demo_pipeline import GradioMultiTalkPipeline; p = GradioMultiTalkPipeline('weights/Wan2.1-I2V-14B-480P', 'weights/chinese-wav2vec2-base')"
```

## License

This demo application follows the same license as the main MultiTalk project (Apache 2.0 License).

## Support

For issues specific to the Gradio demo:
1. Check this README for common solutions
2. Verify model installation and paths
3. Check GPU memory and dependencies
4. Review logs in `multitalk_demo.log`

For general MultiTalk issues, refer to the main project documentation.
