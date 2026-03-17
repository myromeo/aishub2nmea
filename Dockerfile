FROM python:3.11-slim

WORKDIR /app
LABEL org.opencontainers.image.source=https://github.com/myromeo/aishub2nmea

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

CMD ["python", "main.py"]
