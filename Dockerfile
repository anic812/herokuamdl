# Use an official Python runtime as the base image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    ca-certificates
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O /tmp/ffmpeg.tar.xz;
# Extract and install ffmpeg
RUN tar -xf /tmp/ffmpeg.tar.xz -C /tmp && \
    mv /tmp/ffmpeg-*/ffmpeg /usr/local/bin/ && \
    mv /tmp/ffmpeg-*/ffprobe /usr/local/bin/ && \
    rm -rf /tmp/ffmpeg*

RUN wget https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.3.0-beta/N_m3u8DL-RE_v0.3.0-beta_linux-x64_20241203.tar.gz -O /tmp/N_m3u8DL-RE.tar.gz;

# Extract and install N_m3u8DL-RE

RUN tar -xf /tmp/N_m3u8DL-RE.tar.gz -C /tmp && \
    mv /tmp/N_m3u8DL-RE_v0.3.0-beta_linux-x64_20241203/N_m3u8DL-RE /usr/local/bin/ && \
    rm -rf /tmp/N_m3u8DL-RE*

# Set the working directory in the container.
WORKDIR /app

# Allowing read, write, and execute permissions .
RUN chmod 777 /app

# Copy the requirements.txt file to the container.
COPY requirements.txt .

# Install the Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script to the container.
COPY . .

# Set the default command to run when the container starts.
CMD ["python3", "-m", "amdlbot"]
