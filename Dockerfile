# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install required packages directly
RUN pip install --no-cache-dir \
    flask \
    gunicorn \
    flask_sqlalchemy \
    flask_mail \
    python-dotenv

# Expose the port
EXPOSE 5000

# Run the app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "secret_santa:app"]
