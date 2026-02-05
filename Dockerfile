# Use an official Python image
FROM python:3.11-slim

WORKDIR /app

# Architecture detection for downloading correct binaries
ARG TARGETARCH

# Install only required runtime dependencies
# Removed: libopencv-dev, cmake, make, clang, cargo, gcc-arm-none-eabi, libnewlib-*, libstdc++-arm-none-eabi-*
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    git \
    libusb-1.0-0 \
    libpugixml1v5 \
    libpangocairo-1.0-0 \
    libcairo2 \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download prebuilt picotool binary (architecture-aware)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        PICOTOOL_ARCH="aarch64"; \
    else \
        PICOTOOL_ARCH="x86_64"; \
    fi && \
    mkdir -p picotool/build && \
    curl -L "https://github.com/raspberrypi/picotool/releases/download/2.1.1/picotool-2.1.1-linux-${PICOTOOL_ARCH}.tar.gz" | tar xz -C picotool/build --strip-components=1 && \
    chmod +x picotool/build/picotool

# Download prebuilt usvg binary (architecture-aware)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        USVG_ARCH="aarch64-unknown-linux-gnu"; \
    else \
        USVG_ARCH="x86_64-unknown-linux-gnu"; \
    fi && \
    curl -L "https://github.com/ArtRand/usvg/releases/download/v0.34.1/usvg-v0.34.1-${USVG_ARCH}.tar.gz" | tar xz -C /usr/local/bin && \
    chmod +x /usr/local/bin/usvg

# Install Python packages (pcb-tools-extension needs cairocffi, NOT opencv)
RUN pip3 install --no-cache-dir \
    git+https://git.jaseg.de/pcb-tools-extension.git \
    svg-flatten-wasi==3.1.6

# Copy just requirements.txt first to leverage Docker layer cache
COPY requirements.txt .
# Install dependencies — cached unless requirements.txt changes
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your files into the container
# Place this as low in the file as possible since calling this invalidates the docker layer cache
COPY . .

# Expose the port the server runs on
EXPOSE 3333

# Try to fix print()s not showing up immediately in the logs
ENV PYTHONUNBUFFERED=1

# Flask: Run the app (dev)
# Set environment variables
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0
# -u for unbuffered output, so print statements appear in real-time
# CMD ["python3", "-u", "server.py"] 

# Gunicorn: Run the app (production)
# gunicorn server:app --workers 1 --bind 0.0.0.0:8000 --timeout 300
# Only one worker process to avoid concurrency issues (since we're writing files, can't be concurrent)
CMD ["gunicorn", "server:app", "--workers", "4", "--bind", "0.0.0.0:3333", "--capture-output", "--log-level", "debug"]

# To run the gitub built container image locally, do:
#docker pull ghcr.io/devices-lab/makedevice-backend:latest
#docker run -p 3333:3333 ghcr.io/devices-lab/makedevice-backend:latest

# To get requirements.txt with the bare minimum, do:
# pip install pipreqs
# pipreqs . --force
