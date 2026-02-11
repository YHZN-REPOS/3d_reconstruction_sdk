"""
Docker Runner Utility

Provides logging, progress tracking, and error handling for Docker container execution.
"""

import subprocess
import logging
import re
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime

logger = logging.getLogger("my_sdk")


class DockerRunner:
    """
    A utility class for running Docker commands with logging and progress tracking.
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Args:
            log_dir: Directory to save log files. If None, logs are not saved to file.
            progress_callback: Optional callback(stage_name, progress_percent) for progress updates.
        """
        self.log_dir = log_dir
        self.progress_callback = progress_callback
        
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
    
    def run(
        self,
        command: List[str],
        step_name: str = "Docker",
        timeout: Optional[int] = None
    ) -> bool:
        """
        Run a Docker command with logging and progress tracking.
        
        Args:
            command: Docker command as list of strings
            step_name: Name of this step for logging (e.g., "OpenSfM", "OpenSplat")
            timeout: Optional timeout in seconds
            
        Returns:
            bool: True if command succeeded, False otherwise
        """
        logger.info(f"[{step_name}] Starting: {' '.join(command)}")
        
        # Create log file if log_dir is set
        # Create log file if log_dir is set
        log_file_path = None
        log_file_handle = None
        
        if self.log_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\-]', '_', step_name.lower())
            log_file_path = self.log_dir / f"{safe_name}_{timestamp}.log"
            
            # Open file for real-time writing
            try:
                log_file_handle = open(log_file_path, 'w', encoding='utf-8')
                log_file_handle.write(f"# Log started at {datetime.now().isoformat()}\n")
                log_file_handle.write(f"# Command: {' '.join(command)}\n")
                log_file_handle.write("# " + "=" * 50 + "\n\n")
                logger.debug(f"[{step_name}] Logging to {log_file_path}")
            except Exception as e:
                logger.error(f"[{step_name}] Failed to open log file: {e}")
        
        logs: List[str] = []
        return_code = -1
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            for line in process.stdout:
                line = line.rstrip('\n\r')
                line = self._strip_ansi(line) # Remove ANSI color codes
                logs.append(line)
                
                # Log to console
                logger.info(f"[{step_name}] {line}")
                
                # Log to file real-time
                if log_file_handle:
                    log_file_handle.write(line + "\n")
                
                # Try to extract progress
                progress = self._extract_progress(line)
                if progress is not None and self.progress_callback:
                    self.progress_callback(step_name, progress)
            
            # Wait for process to complete
            return_code = process.wait(timeout=timeout)
            
            if return_code != 0:
                logger.error(f"[{step_name}] Failed with exit code {return_code}")
                # We return False but finally block will close file
                return False
            
            logger.info(f"[{step_name}] Completed successfully")
            return True
            
        except KeyboardInterrupt:
            logger.warning(f"[{step_name}] Interrupted by user. Stopping container...")
            try:
                # Try graceful termination first
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                 logger.warning(f"[{step_name}] Process did not stop, killing...")
                 process.kill()
            return False

        except subprocess.TimeoutExpired:
            logger.error(f"[{step_name}] Timeout after {timeout} seconds")
            process.kill()
            return False
            
        except Exception as e:
            logger.error(f"[{step_name}] Unexpected error: {e}")
            return False
            
        finally:
            if log_file_handle:
                if return_code is not None:
                     log_file_handle.write(f"\n# Exit code: {return_code}\n")
                     log_file_handle.write(f"# Finished at {datetime.now().isoformat()}\n")
                log_file_handle.close()

    
    @staticmethod
    def check_gpu_support() -> bool:
        """
        Check if docker supports --gpus all by running a minimal command with alpine.
        """
        import subprocess
        try:
            # Use alpine for a fast, lightweight probe. 
            # If alpine is missing, it will pull it (very fast).
            probe_cmd = ["docker", "run", "--rm", "--gpus", "all", "alpine", "true"]
            result = subprocess.run(
                probe_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=20,
                text=True
            )
            return result.returncode == 0
        except Exception:
            # Fallback check: see if 'nvidia-smi' exists on host as a hint
            try:
                subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                # If host has nvidia-smi but probe failed, it might be a docker-specific issue
                return False 
            except:
                return False

    def _extract_progress(self, line: str) -> Optional[float]:
        """
        Extract progress percentage from log line.
        Supports common patterns like "50%", "50/100", "[=====>    ] 50%"
        """
        # Pattern 1: Direct percentage (e.g., "50%", "Progress: 75.5%")
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
        if match:
            return float(match.group(1))
        
        # Pattern 2: Fraction (e.g., "50/100", "Processing 25 of 50")
        match = re.search(r'(\d+)\s*(?:of|/)\s*(\d+)', line, re.IGNORECASE)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            if total > 0:
                return (current / total) * 100
        
        return None
    
    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape sequences (colors, etc.) from string."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _save_logs(self, log_file: Path, logs: List[str], return_code: int):
        """Save logs to file with metadata."""
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"# Log saved at {datetime.now().isoformat()}\n")
            f.write(f"# Exit code: {return_code}\n")
            f.write("# " + "=" * 50 + "\n\n")
            f.write("\n".join(logs))
        
        logger.debug(f"Logs saved to {log_file}")


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: str = "%(asctime)s [%(levelname)s] %(message)s",
    stream=None
):
    """
    Configure SDK logging.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        log_file: Optional file path to also write logs to
        format_string: Log message format
    """
    handlers = [logging.StreamHandler(stream)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers
    )
    
    # Set SDK logger specifically
    sdk_logger = logging.getLogger("my_sdk")
    sdk_logger.setLevel(level)
