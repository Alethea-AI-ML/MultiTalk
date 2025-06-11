# Demo Assets

This directory contains example assets for the MultiTalk Gradio demo.

## Structure

```
assets/
├── example_images/     # Sample reference images
├── example_audios/     # Sample audio files
└── sample_outputs/     # Example generated videos
```

## Usage

Place example files here to be automatically loaded by the demo interface. The demo will look for:

- `example_images/`: Reference images for single and multi-person generation
- `example_audios/`: Audio files for testing
- `sample_outputs/`: Pre-generated videos to show capabilities

## File Formats

### Images
- Supported: JPG, PNG, BMP, TIFF, WebP
- Recommended: High-resolution, clear faces, good lighting

### Audio
- Supported: WAV, MP3, M4A, FLAC, AAC, OGG
- Recommended: Clear speech, 16kHz sample rate, minimal noise

### Videos
- Output: MP4 with H.264 encoding
- Resolution: 480p (720p support coming soon)
- Frame rate: 25 FPS
