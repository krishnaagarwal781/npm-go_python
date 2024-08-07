# Multi-stage build to reduce image size
FROM python:3.11.2-slim-buster AS builder

# Set working directory
WORKDIR /usr/src/application

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Final, minimal image
FROM python:3.11.2-slim-buster

# Create non-root user
RUN useradd -m appuser

# Set working directory
WORKDIR /usr/src/application

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/src/application /usr/src/application

# Change ownership to non-root user
RUN chown -R appuser /usr/src/application

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 4555

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4555", "--reload", "--workers", "4"]
