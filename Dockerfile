FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


RUN sed -i 's/\r$//' /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV PORT=8080

CMD ["/app/entrypoint.sh"]
