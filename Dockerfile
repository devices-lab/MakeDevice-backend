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

# Install picotool in the "picotool" directory in the repo
RUN git clone https://github.com/raspberrypi/picotool.git picotool && \
    (cd picotool && mkdir build && cd build && cmake .. && make)

# Install picotool in the "picotool" directory in the repo, and its pico-sdk dependency
RUN git clone https://github.com/raspberrypi/picotool.git picotool && \
    git clone https://github.com/raspberrypi/pico-sdk.git && \
    cd pico-sdk && git submodule update --init && cd .. && \
    cd picotool && \
    mkdir build && cd build && \
    cmake .. -DPICO_SDK_PATH=../../pico-sdk && \
    make

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files into the container
COPY . .

# Expose the port the server runs on
EXPOSE 3333

# Set environment variables
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0

# Run the app
# -u for unbuffered output, so print statements appear in real-time
# CMD ["python3", "-u", "server.py"] 

# Run flask server using Gunicorn for production
# gunicorn server:app --workers 1 --bind 0.0.0.0:8000 --timeout 300
# Only one worker process—no concurrency issues (since we're writing files, can't be concurrent)
CMD ["gunicorn", "server:app", "--workers", "1", "--bind", "0.0.0.0:3333"]

#docker pull ghcr.io/devices-lab/makedevice-backend:latest
#docker run -p 3333:3333 ghcr.io/devices-lab/makedevice-backend:latest
