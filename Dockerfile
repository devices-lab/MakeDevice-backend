# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies for picotool + SmartPanelizer
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libusb-1.0-0 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    curl \
    python3 \
    python3-pip \
    python3-wheel \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install prebuilt picotool
# Avoids building pico-sdk + picotool from source
# Choose the appropriate binary based on architecture
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        PICOTOOL_URL="https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.2.0-3/picotool-2.2.0-a4-x86_64-lin.tar.gz"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        PICOTOOL_URL="https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.2.0-3/picotool-2.2.0-a4-aarch64-lin.tar.gz"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -L $PICOTOOL_URL | tar -xz && \
    mv picotool/picotool /usr/local/bin/picotool && \
    chmod +x /usr/local/bin/picotool && \
    rm -rf picotool

# Install prebuilt usvg v0.34.1
# Pull correct binary for architecture and verify checksum
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        USVG_URL="https://github.com/bxnbxrch/usvg-mirror/releases/download/v0.34.1/usvg-0.34.1-x86_64-unknown-linux-gnu.tar.gz"; \
        USVG_SHA="fe76e83e0825570af5c12d544de176eb5b7c21ef77db4d31f3d1bd17f6ed4380"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        USVG_URL="https://github.com/bxnbxrch/usvg-mirror/releases/download/v0.34.1/usvg-0.34.1-aarch64-unknown-linux-gnu.tar.gz"; \
        USVG_SHA="2e09996ccf835b0bb50bda3d953f8870d2a4ac6efa4eb46983f4fcf1c6be78e6"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -L "$USVG_URL" -o /tmp/usvg.tar.gz && \
    echo "$USVG_SHA  /tmp/usvg.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/usvg.tar.gz -C /tmp && \
    mv /tmp/usvg*/usvg /usr/local/bin/usvg && \
    chmod +x /usr/local/bin/usvg && \
    rm -rf /tmp/usvg*


# Install gerborlyze (SmartPanelizer)
RUN pip3 install --no-cache-dir git+https://git.jaseg.de/pcb-tools-extension.git \
    && pip3 install --no-cache-dir svg-flatten-wasi==3.1.6

# Install Python packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port and unbuffer Python output
EXPOSE 3333
ENV PYTHONUNBUFFERED=1

# Run production server
CMD ["gunicorn", "server:app", "--workers", "4", "--bind", "0.0.0.0:3333", "--capture-output", "--log-level", "debug"]

# To run the github built container image locally, do:
#docker pull ghcr.io/devices-lab/makedevice-backend:latest
#docker run -p 3333:3333 ghcr.io/devices-lab/makedevice-backend:latest

# To get requirements.txt with the bare minimum, do:
# pip install pipreqs
# pipreqs . --force
