# Install PDM and use it to export requirements.txt to ensure platform compatibility
FROM python:3.11-slim as requirements-stage

WORKDIR /tmp

RUN pip install pdm

# Copy the pyproject.toml and pdm.lock files to the /tmp directory
# Because it uses ./pdm.lock* (ending with a *), it won't crash if that file is not available
COPY ./pyproject.toml ./pdm.lock* /tmp/

# Generate requirements.txt
RUN pdm export --prod --without-hashes -o requirements.txt

# Build the final image
FROM python:3.11-slim

# ENV LANG=C.UTF-8  # Defined in the base image
ENV LC_ALL=C.UTF-8
ENV LC_TIME=C.UTF-8
ENV LISTEN_PORT=8000
# Enable Python optimizations
ENV PYTHONOPTIMIZE=1

WORKDIR /app

# Copy the requirements.txt file from the previous stage
COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

# Upgrade pip and install / upgrade required packages
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the application code into the container
COPY ./src/terminal_sync ./terminal_sync

EXPOSE $LISTEN_PORT/tcp

# FastAPI has a built-in /docs endpoint that we can use to check whether the server is running properly
HEALTHCHECK CMD curl --fail http://localhost:$LISTEN_PORT/docs || exit 1

ENTRYPOINT python3 -m terminal_sync
