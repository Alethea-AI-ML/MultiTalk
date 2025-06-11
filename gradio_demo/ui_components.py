"""
Enhanced UI Components for MultiTalk Gradio Demo
Provides queue status, progress tracking, and log display components
"""

import gradio as gr
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from queue_manager import queue_manager
from progress_capture import progress_tracker

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def create_queue_status_html(queue_status: Dict[str, Any]) -> str:
    """Create HTML for queue status display"""
    if queue_status["queue_length"] == 0 and not queue_status["active_job"]:
        return """
        <div style="padding: 15px; background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px;">
            <h3 style="margin: 0 0 10px 0; color: #0369a1;">🎯 Queue Status</h3>
            <p style="margin: 0; color: #0369a1; font-weight: bold;">✅ No jobs in queue - Ready for new requests!</p>
        </div>
        """
    
    html = """
    <div style="padding: 15px; background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; color: #92400e;">📊 Queue Status</h3>
    """
    
    # Active job info
    if queue_status["active_job"]:
        active = queue_status["active_job"]
        progress_pct = int(active["progress"] * 100)
        
        html += f"""
        <div style="margin-bottom: 15px; padding: 10px; background: #dcfce7; border-radius: 6px;">
            <h4 style="margin: 0 0 8px 0; color: #166534;">🔄 Currently Processing</h4>
            <p style="margin: 0 0 5px 0;"><strong>Job ID:</strong> {active["job_id"]}</p>
            <p style="margin: 0 0 5px 0;"><strong>Type:</strong> {active["job_type"].title()}</p>
            <p style="margin: 0 0 10px 0;"><strong>Status:</strong> {active["current_step"]}</p>
            <div style="background: #e5e7eb; border-radius: 10px; height: 20px; overflow: hidden;">
                <div style="background: #10b981; height: 100%; width: {progress_pct}%; transition: width 0.3s;"></div>
            </div>
            <p style="margin: 5px 0 0 0; font-size: 12px; color: #374151;">{progress_pct}% Complete</p>
        </div>
        """
    
    # Queue info
    if queue_status["queue_length"] > 0:
        wait_time = format_duration(queue_status["estimated_wait_time"])
        html += f"""
        <div style="margin-bottom: 10px;">
            <p style="margin: 0 0 5px 0;"><strong>📋 Jobs in Queue:</strong> {queue_status["queue_length"]}</p>
            <p style="margin: 0 0 10px 0;"><strong>⏱️ Estimated Wait Time:</strong> {wait_time}</p>
        </div>
        """
        
        # Show first few jobs in queue
        if queue_status["queue_jobs"]:
            html += "<h4 style='margin: 10px 0 5px 0; color: #92400e;'>Next Jobs:</h4><ul style='margin: 0; padding-left: 20px;'>"
            for i, job in enumerate(queue_status["queue_jobs"][:3]):
                created_time = datetime.fromisoformat(job["created_at"].replace('Z', '+00:00')).strftime('%H:%M:%S')
                html += f"<li><strong>{job['job_id']}</strong> ({job['job_type']}) - Added at {created_time}</li>"
            html += "</ul>"
    
    html += "</div>"
    return html

def create_progress_display_html(progress_info: Dict[str, Any]) -> str:
    """Create HTML for detailed progress display"""
    if not progress_info.get("active", False):
        return """
        <div style="padding: 15px; background: #f9fafb; border: 1px solid #d1d5db; border-radius: 8px;">
            <h3 style="margin: 0; color: #6b7280;">📈 Progress Monitor</h3>
            <p style="margin: 10px 0 0 0; color: #6b7280;">No active job</p>
        </div>
        """
    
    progress = progress_info["progress"]
    percentage = progress["percentage"]
    
    html = f"""
    <div style="padding: 15px; background: #f0f9ff; border: 1px solid #3b82f6; border-radius: 8px;">
        <h3 style="margin: 0 0 15px 0; color: #1d4ed8;">📈 Live Progress Monitor</h3>
        
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: bold;">Overall Progress</span>
                <span>{percentage:.1f}%</span>
            </div>
            <div style="background: #e5e7eb; border-radius: 10px; height: 24px; overflow: hidden;">
                <div style="background: linear-gradient(90deg, #3b82f6, #1d4ed8); height: 100%; width: {percentage}%; transition: width 0.5s;"></div>
            </div>
        </div>
    """
    
    if progress["current_step"] and progress["total_steps"]:
        html += f"""
        <div style="margin-bottom: 15px;">
            <p style="margin: 0 0 5px 0;"><strong>Step:</strong> {progress["current_step"]} / {progress["total_steps"]}</p>
        </div>
        """
    
    if progress["description"]:
        html += f"""
        <div style="margin-bottom: 15px; padding: 10px; background: #dbeafe; border-radius: 6px;">
            <p style="margin: 0; font-family: monospace; font-size: 12px;">{progress["description"]}</p>
        </div>
        """
    
    if progress["eta"]:
        html += f"""
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #6b7280;">
            <span>ETA: {progress["eta"]}</span>
            <span>Elapsed: {format_duration(progress["elapsed_time"])}</span>
        </div>
        """
    
    html += "</div>"
    return html

def create_log_display(log_lines: List[str]) -> str:
    """Create formatted log display"""
    if not log_lines:
        return "No recent activity"
    
    # Format logs with syntax highlighting
    formatted_logs = []
    for line in log_lines[-20:]:  # Show last 20 lines
        # Add basic color coding
        if "[ERROR]" in line or "ERROR" in line:
            formatted_logs.append(f'<span style="color: #dc2626;">{line}</span>')
        elif "[WARNING]" in line or "WARNING" in line:
            formatted_logs.append(f'<span style="color: #d97706;">{line}</span>')
        elif "[INFO]" in line or "INFO" in line:
            formatted_logs.append(f'<span style="color: #059669;">{line}</span>')
        elif "%" in line:  # Progress lines
            formatted_logs.append(f'<span style="color: #2563eb; font-weight: bold;">{line}</span>')
        else:
            formatted_logs.append(line)
    
    return "\n".join(formatted_logs)

def get_queue_status() -> str:
    """Get current queue status as HTML"""
    try:
        status = queue_manager.get_queue_status()
        return create_queue_status_html(status)
    except Exception as e:
        return f"""
        <div style="padding: 15px; background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px;">
            <h3 style="margin: 0; color: #dc2626;">❌ Queue Status Error</h3>
            <p style="margin: 10px 0 0 0; color: #dc2626;">Error: {str(e)}</p>
        </div>
        """

def get_progress_status(job_id: str = None) -> str:
    """Get current progress status as HTML"""
    try:
        if job_id:
            progress_info = progress_tracker.get_job_progress_info(job_id)
        else:
            # Get active job progress
            queue_status = queue_manager.get_queue_status()
            if queue_status["active_job"]:
                job_id = queue_status["active_job"]["job_id"]
                progress_info = progress_tracker.get_job_progress_info(job_id)
            else:
                progress_info = {"active": False}
        
        return create_progress_display_html(progress_info)
    except Exception as e:
        return f"""
        <div style="padding: 15px; background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px;">
            <h3 style="margin: 0; color: #dc2626;">❌ Progress Monitor Error</h3>
            <p style="margin: 10px 0 0 0; color: #dc2626;">Error: {str(e)}</p>
        </div>
        """

def get_live_logs(job_id: str = None) -> str:
    """Get live logs for display"""
    try:
        if job_id:
            progress_info = progress_tracker.get_job_progress_info(job_id)
            if progress_info.get("active", False):
                return create_log_display(progress_info["recent_logs"])
        
        # Get logs from active job
        queue_status = queue_manager.get_queue_status()
        if queue_status["active_job"]:
            job_id = queue_status["active_job"]["job_id"]
            progress_info = progress_tracker.get_job_progress_info(job_id)
            if progress_info.get("active", False):
                return create_log_display(progress_info["recent_logs"])
        
        return "No active job logs"
    except Exception as e:
        return f"Error retrieving logs: {str(e)}"

def create_enhanced_status_components():
    """Create enhanced status monitoring components"""
    
    # Queue status component
    queue_status_html = gr.HTML(
        value=get_queue_status(),
        label="Queue Status",
        elem_id="queue_status"
    )
    
    # Progress monitor component
    progress_html = gr.HTML(
        value=get_progress_status(),
        label="Progress Monitor", 
        elem_id="progress_monitor"
    )
    
    # Live logs component
    logs_textbox = gr.Code(
        value=get_live_logs(),
        label="Live Processing Logs",
        language="text",
        lines=15,
        elem_id="live_logs",
        interactive=False
    )
    
    # Auto-refresh components
    def update_status_components():
        return (
            get_queue_status(),
            get_progress_status(),
            get_live_logs()
        )
    
    # Create refresh timer (updates every 2 seconds)
    refresh_timer = gr.Timer(2.0)
    refresh_timer.tick(
        fn=update_status_components,
        outputs=[queue_status_html, progress_html, logs_textbox]
    )
    
    return queue_status_html, progress_html, logs_textbox, refresh_timer

def create_system_info_component():
    """Create system information display"""
    try:
        import torch
        import psutil
        
        # Get system info
        gpu_info = "No GPU" if not torch.cuda.is_available() else f"{torch.cuda.get_device_name(0)}"
        memory_info = f"{psutil.virtual_memory().percent}% used"
        cpu_info = f"{psutil.cpu_percent()}% used"
        
        system_html = f"""
        <div style="padding: 10px; background: #f3f4f6; border-radius: 6px; font-size: 12px;">
            <h4 style="margin: 0 0 8px 0;">🖥️ System Status</h4>
            <p style="margin: 2px 0;"><strong>GPU:</strong> {gpu_info}</p>
            <p style="margin: 2px 0;"><strong>Memory:</strong> {memory_info}</p>
            <p style="margin: 2px 0;"><strong>CPU:</strong> {cpu_info}</p>
        </div>
        """
        
        return gr.HTML(value=system_html, elem_id="system_info")
    except Exception as e:
        return gr.HTML(value=f"<p>System info unavailable: {e}</p>")
