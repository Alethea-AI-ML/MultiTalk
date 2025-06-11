"""
Progress Capture System for MultiTalk Gradio Demo
Captures and formats tqdm output and logging for UI display
"""

import io
import sys
import re
import time
import threading
import contextlib
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ProgressInfo:
    """Information about current progress"""
    percentage: float = 0.0
    current_step: int = 0
    total_steps: int = 0
    rate: Optional[float] = None
    eta: Optional[str] = None
    description: str = ""
    elapsed_time: float = 0.0

class TqdmCapture:
    """Captures tqdm progress output"""
    
    def __init__(self):
        self.captured_output = []
        self.current_progress = ProgressInfo()
        self.lock = threading.Lock()
        self.callbacks: List[Callable[[ProgressInfo], None]] = []
        
        # Regex patterns for parsing tqdm output
        self.tqdm_pattern = re.compile(
            r'(\d+)%\|[█▉▊▋▌▍▎▏ ]*\|\s*(\d+)/(\d+)\s*\[([^\]]+)<([^\]]+),\s*([^\]]+)\]'
        )
        self.simple_progress_pattern = re.compile(r'(\d+)%')
    
    def add_callback(self, callback: Callable[[ProgressInfo], None]):
        """Add a callback to be called when progress updates"""
        with self.lock:
            self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[ProgressInfo], None]):
        """Remove a progress callback"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def parse_tqdm_line(self, line: str) -> Optional[ProgressInfo]:
        """Parse a tqdm progress line"""
        line = line.strip()
        if not line:
            return None
        
        # Try full tqdm pattern first
        match = self.tqdm_pattern.search(line)
        if match:
            percentage = float(match.group(1))
            current = int(match.group(2))
            total = int(match.group(3))
            elapsed = match.group(4)
            eta = match.group(5)
            rate = match.group(6)
            
            return ProgressInfo(
                percentage=percentage,
                current_step=current,
                total_steps=total,
                eta=eta,
                description=line,
                elapsed_time=self._parse_time(elapsed)
            )
        
        # Try simple percentage pattern
        match = self.simple_progress_pattern.search(line)
        if match:
            percentage = float(match.group(1))
            return ProgressInfo(
                percentage=percentage,
                description=line
            )
        
        return None
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string like '01:23' to seconds"""
        try:
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return float(time_str.rstrip('s'))
        except:
            return 0.0
    
    def update_progress(self, line: str):
        """Update progress from a captured line"""
        progress_info = self.parse_tqdm_line(line)
        if progress_info:
            with self.lock:
                self.current_progress = progress_info
                self.captured_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(progress_info)
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")
    
    def get_current_progress(self) -> ProgressInfo:
        """Get current progress information"""
        with self.lock:
            return self.current_progress
    
    def get_recent_output(self, max_lines: int = 50) -> List[str]:
        """Get recent captured output lines"""
        with self.lock:
            return self.captured_output[-max_lines:]
    
    def clear_output(self):
        """Clear captured output"""
        with self.lock:
            self.captured_output.clear()
            self.current_progress = ProgressInfo()

class LogCapture:
    """Captures logging output for display"""
    
    def __init__(self, max_lines: int = 100):
        self.max_lines = max_lines
        self.log_lines: List[str] = []
        self.lock = threading.Lock()
        self.callbacks: List[Callable[[str], None]] = []
    
    def add_callback(self, callback: Callable[[str], None]):
        """Add a callback for new log lines"""
        with self.lock:
            self.callbacks.append(callback)
    
    def add_log_line(self, line: str):
        """Add a new log line"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_line = f"[{timestamp}] {line}"
        
        with self.lock:
            self.log_lines.append(formatted_line)
            if len(self.log_lines) > self.max_lines:
                self.log_lines.pop(0)
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(formatted_line)
                except Exception as e:
                    logger.error(f"Log callback error: {e}")
    
    def get_recent_logs(self, max_lines: int = None) -> List[str]:
        """Get recent log lines"""
        with self.lock:
            if max_lines is None:
                return self.log_lines.copy()
            return self.log_lines[-max_lines:]
    
    def clear_logs(self):
        """Clear all log lines"""
        with self.lock:
            self.log_lines.clear()

class ProgressStreamCapture:
    """Context manager to capture stdout/stderr for progress monitoring"""
    
    def __init__(self, tqdm_capture: TqdmCapture, log_capture: LogCapture):
        self.tqdm_capture = tqdm_capture
        self.log_capture = log_capture
        self.original_stdout = None
        self.original_stderr = None
        self.captured_stdout = io.StringIO()
        self.captured_stderr = io.StringIO()
    
    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create custom stdout/stderr that captures and forwards
        sys.stdout = self._create_capture_stream(self.original_stdout, self._process_stdout)
        sys.stderr = self._create_capture_stream(self.original_stderr, self._process_stderr)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def _create_capture_stream(self, original_stream, processor):
        """Create a stream that captures and processes output"""
        class CaptureStream:
            def __init__(self, original, processor):
                self.original = original
                self.processor = processor
            
            def write(self, text):
                # Write to original stream
                self.original.write(text)
                self.original.flush()
                
                # Process for progress capture
                self.processor(text)
                return len(text)
            
            def flush(self):
                self.original.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        return CaptureStream(original_stream, processor)
    
    def _process_stdout(self, text: str):
        """Process stdout text for progress information"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Check if it looks like a progress line
                if any(indicator in line.lower() for indicator in ['%', 'it/s', 'step', 'epoch']):
                    self.tqdm_capture.update_progress(line)
                else:
                    self.log_capture.add_log_line(line)
    
    def _process_stderr(self, text: str):
        """Process stderr text for error/warning information"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                self.log_capture.add_log_line(f"[STDERR] {line}")

class EnhancedProgressTracker:
    """Enhanced progress tracking system combining queue, tqdm, and logs"""
    
    def __init__(self):
        self.tqdm_capture = TqdmCapture()
        self.log_capture = LogCapture()
        self.active_job_id: Optional[str] = None
        self.job_progress_callbacks: Dict[str, List[Callable]] = {}
    
    def start_job_tracking(self, job_id: str) -> ProgressStreamCapture:
        """Start tracking progress for a specific job"""
        self.active_job_id = job_id
        self.tqdm_capture.clear_output()
        self.log_capture.clear_logs()
        
        # Add progress callback to update queue manager
        def update_queue_progress(progress_info: ProgressInfo):
            from queue_manager import queue_manager
            queue_manager.update_job_progress(
                job_id, 
                progress_info.percentage / 100.0,
                progress_info.description
            )
        
        self.tqdm_capture.add_callback(update_queue_progress)
        
        return ProgressStreamCapture(self.tqdm_capture, self.log_capture)
    
    def add_job_callback(self, job_id: str, callback: Callable):
        """Add a callback for job progress updates"""
        if job_id not in self.job_progress_callbacks:
            self.job_progress_callbacks[job_id] = []
        self.job_progress_callbacks[job_id].append(callback)
    
    def get_job_progress_info(self, job_id: str) -> Dict[str, Any]:
        """Get comprehensive progress information for a job"""
        if job_id != self.active_job_id:
            return {"active": False}
        
        progress_info = self.tqdm_capture.get_current_progress()
        recent_logs = self.log_capture.get_recent_logs(20)
        
        return {
            "active": True,
            "progress": {
                "percentage": progress_info.percentage,
                "current_step": progress_info.current_step,
                "total_steps": progress_info.total_steps,
                "eta": progress_info.eta,
                "description": progress_info.description,
                "elapsed_time": progress_info.elapsed_time
            },
            "recent_logs": recent_logs,
            "tqdm_output": self.tqdm_capture.get_recent_output(10)
        }

# Global progress tracker instance
progress_tracker = EnhancedProgressTracker()
