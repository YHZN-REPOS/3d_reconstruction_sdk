import sys
import argparse
import signal
from my_sdk.core.config import TaskConfig
from my_sdk.core.pipeline import ReconstructionPipeline
from my_sdk.utils.docker_runner import setup_logging

def _signal_handler(sig, frame):
    """Handle SIGTERM by raising KeyboardInterrupt to trigger cleanup in blocking calls."""
    raise KeyboardInterrupt

def main():
    # Register signal handler for SIGTERM (e.g. docker stop or kill)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # Setup basic logging to console immediately
    setup_logging(level=20) # INFO level
    
    parser = argparse.ArgumentParser(description="Custom 3D Reconstruction SDK")
    parser.add_argument("--config", required=True, help="Path to configuration file (JSON or YAML)")
    
    args = parser.parse_args()
    
    try:
        # 1. Parse Config (auto-detects format by extension)
        config = TaskConfig.from_file(args.config)
        
        # 2. Initialize Pipeline (pass config path for backup)
        pipeline = ReconstructionPipeline(config, args.config)
        
        # 3. Run
        success = pipeline.run()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
