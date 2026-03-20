# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Download NLTK stopwords data
ENV PYTHONPATH=/install/lib/python3.12/site-packages
RUN python -c "import nltk; nltk.download('stopwords', download_dir='/install/nltk_data')"

# Stage 2: Final
FROM python:3.12-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash bengala

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /install/nltk_data /home/bengala/nltk_data

ENV NLTK_DATA=/home/bengala/nltk_data

# Copy application source
COPY bengala/ ./bengala/

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R bengala:bengala /app/data

USER bengala

CMD ["python", "-m", "bengala"]
