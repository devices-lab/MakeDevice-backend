# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies for objcopy, picotool, and pico-sdk
RUN apt-get update && apt-get install -y \
    binutils \
    build-essential \
    cmake \
    git \
    libusb-1.0-0-dev \
    pkg-config \
    gcc-arm-none-eabi \
    libnewlib-arm-none-eabi \
    libstdc++-arm-none-eabi-newlib \
    && rm -rf /var/lib/apt/lists/*

# Install gerborlyze dependencies (SmartPanelizer)
RUN apt-get install -y \
    libopencv-dev \
    libpugixml-dev \
    libpangocairo-1.0-0 \
    libpango1.0-dev \
    libcairo2-dev \
    clang \
    make \
    python3 \
    git \
    python3-wheel \
    curl \
    python3-pip \
    python3-venv \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Install gerborlyze (SmartPanelizer)
RUN pip3 install --user git+https://git.jaseg.de/pcb-tools-extension.git
RUN python3 -m pip install svg-flatten-wasi==3.1.6
RUN cargo install usvg --version 0.34.1

# Clone pico-sdk and picotool, then build picotool with PICO_SDK_PATH, then remove pico-sdk
RUN git clone --depth=1 https://github.com/raspberrypi/pico-sdk.git /pico-sdk && \
    git clone https://github.com/raspberrypi/picotool.git picotool && \
    cd picotool && mkdir build && cd build && \
    cmake .. -DPICO_SDK_PATH=/pico-sdk && \
    make && \
    cd /app && rm -rf /pico-sdk

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
