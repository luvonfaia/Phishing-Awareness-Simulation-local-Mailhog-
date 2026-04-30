FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p exports

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "phish_sim.py"]
