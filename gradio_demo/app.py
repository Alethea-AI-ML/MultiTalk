import gradio as gr
import asyncio
import os
import json
import tempfile
import shutil
from pathlib import Path
import logging
from typing import Optional, Tuple, List, Dict, Any
import traceback

from demo_pipeline import GradioMultiTalkPipeline
from input_processor import InputProcessor
from utils import setup_logging, get_example_data, format_error_message
from config import DemoConfig
from ui_components import create_enhanced_status_components, create_system_info_component
from queue_manager import queue_manager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class MultiTalkGradioApp:
    def __init__(self):
        self.config = DemoConfig()
        self.pipeline = None
        self.input_processor = InputProcessor()
        self.temp_dir = tempfile.mkdtemp(prefix="multitalk_demo_")
        logger.info(f"Temporary directory created: {self.temp_dir}")
        
    def initialize_pipeline(self):
        """Initialize the MultiTalk pipeline with error handling"""
        try:
            if self.pipeline is None:
                logger.info("Initializing MultiTalk pipeline...")
                self.pipeline = GradioMultiTalkPipeline(
                    ckpt_dir=self.config.CKPT_DIR,
                    wav2vec_dir=self.config.WAV2VEC_DIR,
                    device_id=self.config.DEVICE_ID
                )
                logger.info("Pipeline initialized successfully")
            return True, "Pipeline ready"
        except Exception as e:
            error_msg = f"Failed to initialize pipeline: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False, error_msg

    def generate_single_person_video(
        self,
        image: Optional[str],
        audio: Optional[str], 
        prompt: str,
        sampling_steps: int,
        text_guide_scale: float,
        audio_guide_scale: float,
        frame_num: int,
        seed: int,
        progress=gr.Progress()
    ) -> Tuple[Optional[str], str]:
        """Generate single person video"""
        try:
            # Initialize pipeline if needed
            success, message = self.initialize_pipeline()
            if not success:
                return None, message
            
            progress(0.1, desc="Validating inputs...")
            
            # Validate inputs
            if not image:
                return None, "Please upload a reference image"
            if not audio:
                return None, "Please upload an audio file"
            if not prompt.strip():
                return None, "Please provide a text prompt"
            
            # Process inputs
            progress(0.2, desc="Processing image...")
            processed_image = self.input_processor.process_image(image)
            
            progress(0.3, desc="Processing audio...")
            processed_audio = self.input_processor.process_single_audio(audio)
            
            # Create input data
            input_data = {
                "prompt": prompt.strip(),
                "cond_image": processed_image,
                "cond_audio": {
                    "person1": processed_audio
                }
            }
            
            # Generate video
            progress(0.4, desc="Generating video...")
            output_path = self.pipeline.generate(
                input_data=input_data,
                sampling_steps=sampling_steps,
                text_guide_scale=text_guide_scale,
                audio_guide_scale=audio_guide_scale,
                frame_num=frame_num,
                seed=seed,
                mode="single",
                progress_callback=lambda p: progress(0.4 + p * 0.5, desc="Generating video...")
            )
            
            progress(1.0, desc="Complete!")
            
            if output_path and os.path.exists(output_path):
                return output_path, "Video generated successfully!"
            else:
                return None, "Video generation failed - no output produced"
                
        except Exception as e:
            error_msg = format_error_message(e)
            logger.error(f"Single person generation failed: {error_msg}")
            logger.error(traceback.format_exc())
            return None, f"Generation failed: {error_msg}"

    def generate_multi_person_video(
        self,
        image: Optional[str],
        audio1: Optional[str],
        audio2: Optional[str],
        audio_type: str,
        prompt: str,
        bbox_person1: Optional[str],
        bbox_person2: Optional[str],
        sampling_steps: int,
        text_guide_scale: float,
        audio_guide_scale: float,
        frame_num: int,
        seed: int,
        progress=gr.Progress()
    ) -> Tuple[Optional[str], str]:
        """Generate multi-person video"""
        try:
            # Initialize pipeline if needed
            success, message = self.initialize_pipeline()
            if not success:
                return None, message
            
            progress(0.1, desc="Validating inputs...")
            
            # Validate inputs
            if not image:
                return None, "Please upload a reference image"
            if not audio1 and not audio2:
                return None, "Please upload at least one audio file"
            if not prompt.strip():
                return None, "Please provide a text prompt"
            
            # Process inputs
            progress(0.2, desc="Processing image...")
            processed_image = self.input_processor.process_image(image)
            
            progress(0.3, desc="Processing audio files...")
            processed_audio1 = self.input_processor.process_single_audio(audio1) if audio1 else "None"
            processed_audio2 = self.input_processor.process_single_audio(audio2) if audio2 else "None"
            
            # Create input data
            input_data = {
                "prompt": prompt.strip(),
                "cond_image": processed_image,
                "audio_type": audio_type,
                "cond_audio": {
                    "person1": processed_audio1,
                    "person2": processed_audio2
                }
            }
            
            # Add bounding boxes if provided
            if bbox_person1 or bbox_person2:
                bbox_dict = {}
                if bbox_person1:
                    try:
                        bbox_dict["person1"] = [int(x.strip()) for x in bbox_person1.split(",")]
                    except:
                        return None, "Invalid bounding box format for person 1. Use: x_min,y_min,x_max,y_max"
                if bbox_person2:
                    try:
                        bbox_dict["person2"] = [int(x.strip()) for x in bbox_person2.split(",")]
                    except:
                        return None, "Invalid bounding box format for person 2. Use: x_min,y_min,x_max,y_max"
                
                if bbox_dict:
                    input_data["bbox"] = bbox_dict
            
            # Generate video
            progress(0.4, desc="Generating video...")
            output_path = self.pipeline.generate(
                input_data=input_data,
                sampling_steps=sampling_steps,
                text_guide_scale=text_guide_scale,
                audio_guide_scale=audio_guide_scale,
                frame_num=frame_num,
                seed=seed,
                mode="multi",
                progress_callback=lambda p: progress(0.4 + p * 0.5, desc="Generating video...")
            )
            
            progress(1.0, desc="Complete!")
            
            if output_path and os.path.exists(output_path):
                return output_path, "Video generated successfully!"
            else:
                return None, "Video generation failed - no output produced"
                
        except Exception as e:
            error_msg = format_error_message(e)
            logger.error(f"Multi-person generation failed: {error_msg}")
            logger.error(traceback.format_exc())
            return None, f"Generation failed: {error_msg}"

    def create_interface(self):
        """Create the Gradio interface"""
        
        # Custom CSS for better styling
        css = """
        .gradio-container {
            max-width: 1400px !important;
        }
        .output-video {
            max-height: 500px;
        }
        .error-message {
            color: #ff4444;
            font-weight: bold;
        }
        .success-message {
            color: #44ff44;
            font-weight: bold;
        }
        #queue_status {
            margin-bottom: 10px;
        }
        #progress_monitor {
            margin-bottom: 10px;
        }
        #live_logs {
            font-family: 'Courier New', monospace;
            font-size: 11px;
            background: #1f2937;
            color: #f9fafb;
        }
        #system_info {
            margin-top: 10px;
        }
        .status-panel {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
        }
        """
        
        with gr.Blocks(css=css, title="MultiTalk: Audio-Driven Video Generation") as demo:
            gr.Markdown("""
            # 🎬 MultiTalk: Audio-Driven Multi-Person Video Generation
            
            Generate realistic conversational videos with synchronized lip movements from audio and reference images.
            
            **Features:**
            - 💬 Single & multi-person conversation generation
            - 🎤 High-quality lip synchronization
            - 👥 Interactive character control via prompts
            - 📺 480p & 720p output support
            """)
            
            # Enhanced Status Dashboard
            with gr.Row():
                with gr.Column(scale=2):
                    # Create enhanced status components
                    queue_status_html, progress_html, logs_textbox, refresh_timer = create_enhanced_status_components()
                with gr.Column(scale=1):
                    # System info
                    system_info = create_system_info_component()
            
            with gr.Tabs():
                # Single Person Tab
                with gr.TabItem("👤 Single Person"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Input")
                            single_image = gr.Image(
                                label="Reference Image",
                                type="filepath",
                                height=300
                            )
                            single_audio = gr.Audio(
                                label="Audio File",
                                type="filepath"
                            )
                            single_prompt = gr.Textbox(
                                label="Description Prompt",
                                placeholder="Describe the scene, person, and setting...",
                                lines=3,
                                value="A person speaking passionately in a professional setting."
                            )
                            
                            with gr.Accordion("⚙️ Advanced Settings", open=False):
                                gr.Markdown("**Note:** Video length is automatically calculated from audio duration (25 FPS)")
                                single_steps = gr.Slider(10, 50, value=40, step=1, label="Sampling Steps")
                                single_text_scale = gr.Slider(1.0, 10.0, value=5.0, step=0.5, label="Text Guidance Scale")
                                single_audio_scale = gr.Slider(1.0, 10.0, value=4.0, step=0.5, label="Audio Guidance Scale")
                                single_seed = gr.Number(value=42, label="Seed (-1 for random)")
                            
                            single_generate_btn = gr.Button("🎬 Generate Video", variant="primary", size="lg")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### Output")
                            single_output_video = gr.Video(
                                label="Generated Video",
                                height=400
                            )
                            single_status = gr.Textbox(
                                label="Status",
                                interactive=False,
                                max_lines=3
                            )
                
                # Multi-Person Tab
                with gr.TabItem("👥 Multi-Person"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Input")
                            multi_image = gr.Image(
                                label="Reference Image",
                                type="filepath",
                                height=300
                            )
                            
                            with gr.Row():
                                multi_audio1 = gr.Audio(
                                    label="Person 1 Audio",
                                    type="filepath"
                                )
                                multi_audio2 = gr.Audio(
                                    label="Person 2 Audio",
                                    type="filepath"
                                )
                            
                            multi_audio_type = gr.Radio(
                                choices=["add", "para"],
                                value="add",
                                label="Audio Mixing Mode",
                                info="add: sequential speaking, para: parallel speaking"
                            )
                            
                            multi_prompt = gr.Textbox(
                                label="Description Prompt",
                                placeholder="Describe the conversation scene...",
                                lines=3,
                                value="Two people engaged in a heartfelt conversation."
                            )
                            
                            with gr.Accordion("📍 Bounding Boxes (Optional)", open=False):
                                gr.Markdown("Specify person locations as: x_min,y_min,x_max,y_max")
                                multi_bbox1 = gr.Textbox(
                                    label="Person 1 Bounding Box",
                                    placeholder="160,120,1280,1080"
                                )
                                multi_bbox2 = gr.Textbox(
                                    label="Person 2 Bounding Box", 
                                    placeholder="160,1320,1280,2280"
                                )
                            
                            with gr.Accordion("⚙️ Advanced Settings", open=False):
                                gr.Markdown("**Note:** Video length is automatically calculated from audio duration (25 FPS)")
                                multi_steps = gr.Slider(10, 50, value=40, step=1, label="Sampling Steps")
                                multi_text_scale = gr.Slider(1.0, 10.0, value=5.0, step=0.5, label="Text Guidance Scale")
                                multi_audio_scale = gr.Slider(1.0, 10.0, value=4.0, step=0.5, label="Audio Guidance Scale")
                                multi_seed = gr.Number(value=42, label="Seed (-1 for random)")
                            
                            multi_generate_btn = gr.Button("🎬 Generate Video", variant="primary", size="lg")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### Output")
                            multi_output_video = gr.Video(
                                label="Generated Video",
                                height=400
                            )
                            multi_status = gr.Textbox(
                                label="Status",
                                interactive=False,
                                max_lines=3
                            )
                
                # Monitoring Dashboard Tab
                with gr.TabItem("📊 Monitor"):
                    gr.Markdown("""
                    ### Live Processing Monitor
                    
                    Real-time view of queue status, progress, and system logs.
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            # Detailed queue status
                            queue_status_detailed = queue_status_html
                            
                            # Detailed progress monitor
                            progress_detailed = progress_html
                        
                        with gr.Column(scale=1):
                            # Live logs with more space
                            logs_detailed = logs_textbox
                
                # Examples Tab
                with gr.TabItem("📚 Examples"):
                    gr.Markdown("""
                    ### Example Inputs
                    
                    Here are some example configurations to get you started:
                    """)
                    
                    examples_data = get_example_data()
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Single Person Example")
                            gr.Examples(
                                examples=examples_data["single"],
                                inputs=[single_image, single_audio, single_prompt],
                                label="Single Person Examples"
                            )
                        
                        with gr.Column():
                            gr.Markdown("#### Multi-Person Example")
                            gr.Examples(
                                examples=examples_data["multi"],
                                inputs=[multi_image, multi_audio1, multi_audio2, multi_prompt],
                                label="Multi-Person Examples"
                            )
            
            # Event handlers
            single_generate_btn.click(
                fn=self.generate_single_person_video,
                inputs=[
                    single_image, single_audio, single_prompt,
                    single_steps, single_text_scale, single_audio_scale,
                    81, single_seed  # Use dummy frame number (will be overridden)
                ],
                outputs=[single_output_video, single_status],
                show_progress=True
            )
            
            multi_generate_btn.click(
                fn=self.generate_multi_person_video,
                inputs=[
                    multi_image, multi_audio1, multi_audio2, multi_audio_type,
                    multi_prompt, multi_bbox1, multi_bbox2,
                    multi_steps, multi_text_scale, multi_audio_scale,
                    81, multi_seed  # Use dummy frame number (will be overridden)
                ],
                outputs=[multi_output_video, multi_status],
                show_progress=True
            )
        
        return demo

    def cleanup(self):
        """Cleanup temporary files and resources"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            
            if self.pipeline:
                self.pipeline.cleanup()
                logger.info("Pipeline cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def main():
    """Main function to run the Gradio app"""
    app = MultiTalkGradioApp()
    
    try:
        demo = app.create_interface()
        
        # Launch the app
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
    
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.error(traceback.format_exc())
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()
