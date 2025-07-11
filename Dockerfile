# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install objcopy
RUN apt-get update && apt-get install -y binutils && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Flask app code
COPY . .

# Set environment variables
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0

# Expose the port Flask runs on
EXPOSE 3333

# Run the app
CMD ["python3", "server.py"]
