FROM python:3.11-slim

WORKDIR /app

# TODO: install only the backend runtime dependencies required by the final API.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# TODO: replace the development command with a production-ready entrypoint if needed.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]