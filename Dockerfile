# Use an official Python image
FROM python:3.11-slim

WORKDIR /app

# Enable multi-arch builds (e.g., for ARM Macs vs x86_64 servers)
ARG TARGETARCH

# Install runtime dependencies for picotool, gerbolyze (SmartPanelizer), and general tooling
# Using --no-install-recommends and runtime-only libs to keep image small
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

# Install picotool for RP2040 firmware manipulation
# Using prebuilt binaries instead of building from source to speed up builds and reduce image size
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        PICOTOOL_ARCH="aarch64"; \
    else \
        PICOTOOL_ARCH="x86_64"; \
    fi && \
    mkdir -p picotool/build && \
    curl -L "https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.2.0-3/picotool-2.2.0-a4-${PICOTOOL_ARCH}-lin.tar.gz" | tar xz -C picotool/build && \
    chmod +x picotool/build/picotool

# Install usvg for SVG processing (required by gerbolyze)
# resvg project only provides x86_64 binaries, so we must build from source on ARM
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

# Install gerbolyze (SmartPanelizer) for PCB artwork processing
RUN pip3 install --no-cache-dir \
    git+https://git.jaseg.de/pcb-tools-extension.git \
    svg-flatten-wasi==3.1.6

# Copy requirements.txt first so Docker can cache this layer
# Rebuilds only happen when requirements.txt changes, not on every code change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files into the container
# Keep this as late as possible to maximize cache hits on earlier layers
COPY . .

# Expose the port the server runs on
EXPOSE 3333

# Force Python to flush stdout/stderr immediately so logs appear in real-time
ENV PYTHONUNBUFFERED=1

# --- Development mode (Flask) ---
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0
# CMD ["python3", "-u", "server.py"] 

# --- Production mode (Gunicorn) ---
# Using multiple workers for better throughput
CMD ["gunicorn", "server:app", "--workers", "4", "--bind", "0.0.0.0:3333", "--capture-output", "--log-level", "debug"]

# To run the gitub built container image locally, do:
#docker pull ghcr.io/devices-lab/makedevice-backend:latest
#docker run -p 3333:3333 ghcr.io/devices-lab/makedevice-backend:latest

# To get requirements.txt with the bare minimum, do:
# pip install pipreqs
# pipreqs . --force
