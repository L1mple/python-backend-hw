# Use an official Python runtime as a parent image
FROM python:3.9-alpine AS base
ARG PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=500

RUN python -m pip install --upgrade pip

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install "fastapi[standard]"  
RUN pip install sqlalchemy
# Make port 8000 available to the world outside this container
EXPOSE 8080

# Run app.py when the container launches
# CMD ["python", "app.py"]
FROM base AS local
CMD ["fastapi", "dev", "/app/shop_api/main.py",  "--port", "8080", "--host", "0.0.0.0"]