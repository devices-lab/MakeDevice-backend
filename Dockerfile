# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies for picotool + SmartPanelizer
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    libusb-1.0-0 \
    libpangocairo-1.0-0 \
    libpango1.0-0 \
    libcairo2 \
    curl \
    python3 \
    python3-pip \
    python3-wheel \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install prebuilt picotool
# Avoids building pico-sdk + picotool from source
RUN curl -L https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.2.0-3/picotool-2.2.0-a4-x86_64-lin.tar.gz \
    | tar -xz && \
    mv picotool/picotool /usr/local/bin/picotool && \
    chmod +x /usr/local/bin/picotool && \
    rm -rf picotool

# Install prebuilt usvg
# Avoids compiling Rust toolchain
RUN curl -L -o /usr/local/bin/usvg \
    https://github.com/bxnbxrch/usvg-with-binaries/releases/download/v1.0/usvg && \
    echo "1729746dbaf087d2d91f28cf102b9746a8ab5b978bf1543a8632d6674132ec8d  /usr/local/bin/usvg" | sha256sum -c - && \
    chmod +x /usr/local/bin/usvg

# Install gerborlyze (SmartPanelizer)
RUN pip3 install --user git+https://git.jaseg.de/pcb-tools-extension.git
RUN python3 -m pip install svg-flatten-wasi==3.1.6

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
