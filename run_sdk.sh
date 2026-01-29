#!/bin/bash

# Usage: ./run_sdk.sh [--dev] <path_to_config.json>
# --dev: Development mode, mounts local code directory (no rebuild needed)

DEV_MODE=false
CONF_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        *)
            CONF_FILE=$1
            shift
            ;;
    esac
done

if [ -z "$CONF_FILE" ]; then
    echo "Usage: ./run_sdk.sh [--dev] <absolute_path_to_config.json>"
    echo "  --dev  Development mode: mounts local my_sdk/ directory (no rebuild needed)"
    exit 1
fi

# Ensure config path is absolute
CONF_PATH=$(realpath "$CONF_FILE")
CONF_DIR=$(dirname "$CONF_PATH")
CONF_NAME=$(basename "$CONF_PATH")

# Get the SDK source directory (where this script is located)
SDK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Docker-Out-Of-Docker (DooD) Run Command
# 1. -v /var/run/docker.sock:/var/run/docker.sock :: Allows SDK to verify and start sibling containers
# 2. -v $CONF_DIR:/workspace :: Mounts the config directory so the SDK can read the JSON
# 3. --network host :: Optional, but helpful for local network access
# NOTE: The "working_dir" in your JSON must be an absolute path on the HOST machine, 
# because the sibling OpenSfM/OpenSplat containers will use it directly.

if [ "$DEV_MODE" = true ]; then
    echo "Starting SDK Container (DEV MODE - local code mounted)..."
    docker run --rm -it \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$CONF_DIR":/workspace \
        -v "$SDK_DIR/my_sdk":/app/my_sdk \
        my-sdk-image \
        --config "/workspace/$CONF_NAME"
else
    echo "Starting SDK Container..."
    docker run --rm -it \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$CONF_DIR":/workspace \
        my-sdk-image \
        --config "/workspace/$CONF_NAME"
fi
