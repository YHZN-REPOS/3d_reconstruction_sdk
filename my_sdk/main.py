import sys
import argparse
import signal
from my_sdk.core.config import TaskConfig
from my_sdk.core.pipeline import ReconstructionPipeline
from my_sdk.utils.docker_runner import setup_logging


class _TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        for stream in self.streams:
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return False

def _signal_handler(sig, frame):
    """Handle SIGTERM by raising KeyboardInterrupt to trigger cleanup in blocking calls."""
    raise KeyboardInterrupt

def main():
    # Register signal handler for SIGTERM (e.g. docker stop or kill)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    parser = argparse.ArgumentParser(description="Custom 3D Reconstruction SDK")
    parser.add_argument("--config", required=True, help="Path to configuration file (JSON or YAML)")
    
    args = parser.parse_args()
    
    try:
        # 1. Parse Config (auto-detects format by extension)
        config = TaskConfig.from_file(args.config)
        
        # 2. Initialize Pipeline (pass config path for backup)
        pipeline = ReconstructionPipeline(config, args.config)

        # 3. Setup logging (console + unified sdk.log)
        log_path = pipeline.context.log_path / "sdk.log"
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        log_file_handle = None

        try:
            setup_logging(level=20, log_file=log_path, stream=orig_stderr)  # INFO level
            log_file_handle = open(log_path, "a", encoding="utf-8")
            sys.stdout = _TeeStream(orig_stdout, log_file_handle)
            sys.stderr = _TeeStream(orig_stderr, log_file_handle)

            # 4. Run
            success = pipeline.run()
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            if log_file_handle:
                log_file_handle.close()

        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
