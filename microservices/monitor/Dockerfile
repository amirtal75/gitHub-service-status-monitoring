# Use a Python 3.9 slim image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker cache for dependencies
COPY requirements.txt .

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y curl net-tools

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port for FastAPI
EXPOSE 5000

# Default command to run the app
CMD ["python", "app.py"]
