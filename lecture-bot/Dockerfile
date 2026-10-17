FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Download the speech model at build time so the first lecture is not slow
ARG WHISPER_MODEL=large-v3-turbo
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')"

CMD ["python", "bot.py"]
