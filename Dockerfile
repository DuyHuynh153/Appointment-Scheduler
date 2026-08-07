FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations

# TODO: once migrations exist (migrations/versions/ is currently empty),
# switch this to run `alembic upgrade head` before starting uvicorn,
# e.g. via a small entrypoint script.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
