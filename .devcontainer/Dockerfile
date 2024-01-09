# Base Image
ARG VARIANT=3-bullseye
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# Our working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN curl -sSL https://install.python-poetry.org | python -
COPY poetry.lock pyproject.toml /app/

ENV PATH="${PATH}:/root/.local/bin"
RUN poetry config virtualenvs.create false && poetry install

RUN pip install "python-telegram-bot[job-queue]"