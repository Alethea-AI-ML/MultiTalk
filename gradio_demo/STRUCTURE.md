# MultiTalk Gradio Demo - File Structure

This document outlines the complete file structure and purpose of each component in the MultiTalk Gradio demo.

## Directory Structure

```
gradio_demo/
├── app.py                    # Main Gradio application
├── demo_pipeline.py          # MultiTalk pipeline wrapper
├── input_processor.py        # Input validation and preprocessing
├── utils.py                  # Utility functions and helpers
├── config.py                 # Configuration settings
├── launch.py                 # Launcher script with checks
├── install.sh                # Installation script
├── requirements_demo.txt     # Demo-specific dependencies
├── README_demo.md           # Comprehensive documentation
├── STRUCTURE.md             # This file
└── assets/                  # Demo assets directory
    ├── README.md            # Assets documentation
    ├── example_images/      # Sample reference images
    ├── example_audios/      # Sample audio files
    └── sample_outputs/      # Example generated videos
```

## Core Components

### `app.py` - Main Application
- **Purpose**: Primary Gradio interface with tabs for single/multi-person generation
- **Features**: 
  - Interactive web UI with progress tracking
  - Input validation and error handling
  - Advanced parameter controls
  - Example integration
- **Key Classes**: `MultiTalkGradioApp`

### `demo_pipeline.py` - Pipeline Wrapper
- **Purpose**: Wraps MultiTalk pipeline for Gradio integration
- **Features**:
  - Audio embedding generation
  - Video generation with progress callbacks
  - Resource management and cleanup
  - Error handling and recovery
- **Key Classes**: `GradioMultiTalkPipeline`

### `input_processor.py` - Input Processing
- **Purpose**: Validates and preprocesses user inputs
- **Features**:
  - Image format validation and conversion
  - Audio format validation and normalization
  - File size and quality checks
  - Automatic preprocessing
- **Key Classes**: `InputProcessor`

### `utils.py` - Utilities
- **Purpose**: Shared utility functions and helpers
- **Features**:
  - Audio processing functions
  - Error message formatting
  - Dependency checking
  - Example data loading
- **Key Functions**: 
  - `audio_prepare_single()`, `audio_prepare_multi()`
  - `get_embedding()`, `loudness_norm()`
  - `check_dependencies()`, `validate_model_paths()`

### `config.py` - Configuration
- **Purpose**: Centralized configuration management
- **Features**:
  - Environment variable handling
  - Default parameter settings
  - Path validation
  - Model information
- **Key Classes**: `DemoConfig`

### `launch.py` - Launcher Script
- **Purpose**: Smart launcher with pre-flight checks
- **Features**:
  - Dependency verification
  - Model file validation
  - GPU detection
  - Command-line options
- **Usage**: `python launch.py --help`

## Installation & Setup

### Quick Start
```bash
# Install dependencies
./install.sh

# Launch demo
python launch.py
```

### Manual Setup
```bash
# Install requirements
pip install -r requirements_demo.txt

# Set environment variables
export MULTITALK_CKPT_DIR="../weights/Wan2.1-I2V-14B-480P"
export MULTITALK_WAV2VEC_DIR="../weights/chinese-wav2vec2-base"

# Run demo
python app.py
```

## Usage Modes

### Single Person Generation
1. Upload reference image
2. Upload audio file
3. Write description prompt
4. Adjust settings (optional)
5. Generate video

### Multi-Person Generation
1. Upload reference image (with 2 people)
2. Upload separate audio files for each person
3. Choose audio mixing mode (sequential/parallel)
4. Set bounding boxes (optional)
5. Write description prompt
6. Generate video

## Configuration Options

### Environment Variables
- `MULTITALK_CKPT_DIR`: Model checkpoint directory
- `MULTITALK_WAV2VEC_DIR`: Wav2Vec model directory
- `MULTITALK_DEVICE_ID`: GPU device ID
- `MULTITALK_MAX_USERS`: Maximum concurrent users
- `MULTITALK_MAX_QUEUE`: Maximum queue size

### Generation Parameters
- **Sampling Steps**: Quality vs speed tradeoff (10-50)
- **Text Guidance Scale**: Prompt adherence (1-10)
- **Audio Guidance Scale**: Audio synchronization (1-10)
- **Frame Number**: Video length (81-201 frames)
- **Seed**: Reproducibility control

## Input Requirements

### Images
- **Formats**: JPG, PNG, BMP, TIFF, WebP
- **Size**: 64x64 to 2048x2048 pixels
- **Quality**: High resolution, clear faces, good lighting

### Audio
- **Formats**: WAV, MP3, M4A, FLAC, AAC, OGG
- **Duration**: 0.5 to 60 seconds
- **Quality**: Clear speech, minimal noise
- **Processing**: Automatic conversion to 16kHz WAV

## Output Format

### Videos
- **Format**: MP4 with H.264 encoding
- **Resolution**: 480p (720p support planned)
- **Frame Rate**: 25 FPS
- **Audio**: Synchronized with lip movements

## Error Handling

### Input Validation
- File format checking
- Size and duration limits
- Quality assessment
- Automatic preprocessing

### Generation Errors
- GPU memory management
- Model loading failures
- Processing timeouts
- Resource cleanup

### User Feedback
- Clear error messages
- Troubleshooting suggestions
- Progress indicators
- Status updates

## Performance Considerations

### GPU Requirements
- **Minimum**: 8GB VRAM
- **Recommended**: 12GB+ VRAM
- **CPU Fallback**: Available but very slow

### Memory Management
- Automatic model offloading
- Temporary file cleanup
- GPU memory clearing
- Resource monitoring

### Optimization Tips
- Reduce frame count for faster generation
- Lower sampling steps for speed
- Use appropriate guidance scales
- Monitor GPU utilization

## Development & Extension

### Adding Features
1. **New Models**: Update `config.py` and `demo_pipeline.py`
2. **Input Types**: Extend `input_processor.py`
3. **UI Changes**: Modify `app.py`
4. **Processing**: Add functions to `utils.py`

### Testing
```bash
# Test components
python -c "from utils import check_dependencies; print(check_dependencies())"
python -c "from config import config; print(config.get_model_info())"

# Test pipeline
python -c "from demo_pipeline import GradioMultiTalkPipeline; p = GradioMultiTalkPipeline('weights/Wan2.1-I2V-14B-480P', 'weights/chinese-wav2vec2-base')"
```

### Deployment
- Use `launch.py` for production deployment
- Configure environment variables appropriately
- Monitor resource usage and performance
- Set up proper logging and monitoring

## Troubleshooting

### Common Issues
1. **Model not found**: Check paths and downloads
2. **GPU memory**: Reduce parameters or close other applications
3. **Dependencies**: Install missing packages
4. **Audio processing**: Check file formats and quality

### Debug Mode
```bash
# Enable detailed logging
python launch.py --skip-checks

# Check system status
python -c "from utils import check_dependencies, validate_model_paths; print(check_dependencies()); print(validate_model_paths('../weights/Wan2.1-I2V-14B-480P', '../weights/chinese-wav2vec2-base'))"
```

This structure provides a complete, production-ready Gradio demo for MultiTalk with comprehensive error handling, input validation, and user-friendly features.
