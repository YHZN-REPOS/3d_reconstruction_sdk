# Use a lightweight Python base image
# Use ARG for platform to avoid Docker warning
ARG TARGETPLATFORM=linux/amd64
FROM python:3.9-slim

# Use Aliyun mirror for faster downloads in China
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy SDK code
COPY my_sdk /app/my_sdk

# Set Python path so my_sdk can be imported
ENV PYTHONPATH=/app

# Install Python dependencies
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple pydantic pyyaml "numpy<2.0.0" "opencv-python-headless>=4.5"

# Entrypoint to run the SDK CLI
# User can pass arguments like: --config /data/config.json
ENTRYPOINT ["python", "-m", "my_sdk.main"]
