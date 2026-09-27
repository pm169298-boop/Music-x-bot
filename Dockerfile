FROM python:3.11-slim

WORKDIR /app

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ffmpeg curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "main.py"]
