# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the console
ENV PYTHONUNBUFFERED True

# Set the working directory
WORKDIR /app

# Copy local code to the container image.
COPY . /app

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Expose the standard Flask port
EXPOSE 5000

# Run the Waitress production server
CMD ["python", "run.py"]
