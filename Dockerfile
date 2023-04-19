FROM python:3.11

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV LC_TIME=C.UTF-8
ENV LISTEN_PORT=8000

WORKDIR /app


# COPY requirements.txt requirements.txt

# RUN pip install --no-cache-dir --upgrade -r requirements.txt

# COPY ./src/terminal_sync .

RUN pip install pdm

COPY . .

RUN pdm install --prod

EXPOSE $LISTEN_PORT/tcp

# FastAPI has a built-in /docs endpoint that we can use to check whether the server is running properly
HEALTHCHECK CMD curl --fail http://localhost:$LISTEN_PORT/docs || exit 1

# CMD ["pdm", "run", "uvicorn", "terminal_sync.api:app", "--host", "0.0.0.0", "--port", $LISTEN_PORT]
CMD pdm run uvicorn terminal_sync.api:app --host 0.0.0.0 --port $LISTEN_PORT
