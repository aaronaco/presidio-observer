FROM python:3.9-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry>=2.1.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
# We use --no-root because it's a non-package project (package-mode = false handles this too)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of the application
COPY main.py database.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
