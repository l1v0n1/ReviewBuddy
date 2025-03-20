FROM python:3.10-slim

WORKDIR /app

# Install Node.js for eslint
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install eslint globally
RUN npm install -g eslint@8.42.0

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the action code
COPY src/ /app/src/
COPY entrypoint.sh /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Run the action
ENTRYPOINT ["/app/entrypoint.sh"] 