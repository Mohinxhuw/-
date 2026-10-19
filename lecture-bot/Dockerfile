FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

# YouTube now needs a JavaScript runtime for yt-dlp to read its pages
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Download the speech model at build time so the first lecture is not slow
ARG WHISPER_MODEL=large-v3-turbo
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')"

# YouTube changes often and old yt-dlp versions stop working: update it at every start.
CMD ["sh", "-c", "pip install -q --no-cache-dir -U 'yt-dlp[default]' || true; exec python bot.py"]
