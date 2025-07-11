# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install objcopy and other dependencies needed for building picotool
RUN apt-get update && apt-get install -y \
    binutils \
    build-essential \
    cmake \
    git \
    libusb-1.0-0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install picotool in the "picotool" directory in the repo
RUN git clone https://github.com/raspberrypi/picotool.git picotool && \
    (cd picotool && mkdir build && cd build && cmake .. && make)

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Flask app code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose the port Flask runs on
EXPOSE 3333

# Run the app
# -u for unbuffered output, so print statements appear in real-time
# CMD ["python3", "-u", "server.py"] 

# Run flask server using Gunicorn for production
# gunicorn server:app --workers 1 --bind 0.0.0.0:8000 --timeout 300
# Only one worker process—no concurrency issues (since we're writing files, can't be concurrent)
CMD ["gunicorn", "server:app", "--workers", "1", "--bind", "0.0.0.0:3333"]

#docker pull ghcr.io/devices-lab/makedevice-backend:latest
#docker run -p 3333:3333 ghcr.io/devices-lab/makedevice-backend:latest
