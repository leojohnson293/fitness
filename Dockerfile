# Use official Python slim image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install dependencies first (cached layer — only rebuilds if requirements.txt changes)
COPY fitness_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY fitness_app/ .

# Copy db migrations
COPY db/ /db

# Expose port (overridden by docker-compose)
EXPOSE 8000

# Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
