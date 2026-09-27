# ==============================================================================
#  Music-x-bot — Single file edition
#  Ek hi main.py me: engine + plugins + helpers + 13 locales + fonts
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# ffmpeg  -> streaming/encoding ke liye
# curl/git-> cookies + repo tools
# deno    -> yt-dlp ke naye YouTube challenges ke liye (optional but recommended)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ffmpeg curl git ca-certificates unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# data/ me database + backups bante hain -> volume mount karne ki salah dete hain:
#   docker run -v $PWD/data:/app/data --env-file .env musicxbot
VOLUME ["/app/data"]

CMD ["python3", "main.py"]
