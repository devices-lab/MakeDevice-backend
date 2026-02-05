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

# Download prebuilt picotool binary from pico-sdk-tools (architecture-aware)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        PICOTOOL_ARCH="aarch64"; \
    else \
        PICOTOOL_ARCH="x86_64"; \
    fi && \
    mkdir -p picotool/build && \
    curl -L "https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.2.0-3/picotool-2.2.0-a4-${PICOTOOL_ARCH}-lin.tar.gz" | tar xz -C picotool/build && \
    chmod +x picotool/build/picotool

# Download prebuilt usvg binary (x86_64) or install via cargo (arm64)
# Note: resvg project only provides x86_64 Linux binaries
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        apt-get update && apt-get install -y --no-install-recommends cargo && \
        cargo install usvg --version 0.34.1 && \
        cp /root/.cargo/bin/usvg /usr/local/bin/ && \
        apt-get purge -y cargo && apt-get autoremove -y && \
        rm -rf /var/lib/apt/lists/* /root/.cargo; \
    else \
        curl -L "https://github.com/linebender/resvg/releases/download/v0.46.0/usvg-linux-x86_64.tar.gz" | tar xz -C /usr/local/bin && \
        chmod +x /usr/local/bin/usvg; \
    fi

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
