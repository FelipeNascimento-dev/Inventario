FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=setup.settings
ENV DEBUG=False

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "setup.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "4", "--threads", "2", "--timeout", "60", \
     "--max-requests", "1000", "--max-requests-jitter", "100"]
