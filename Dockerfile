# Base Image
FROM python:3.8

# Our working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN curl -sSL https://install.python-poetry.org | python -
COPY poetry.lock pyproject.toml

RUN poetry config virtualenvs.create false && poetry install

# Run the flask application
CMD ["python", "app.py"]