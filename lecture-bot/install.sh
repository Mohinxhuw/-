#!/usr/bin/env bash
# One-step setup on a fresh Ubuntu server:
#   curl -fsSL https://raw.githubusercontent.com/mohinxhuw/-/ccr-4886f54a-w71o4y/lecture-bot/install.sh | sudo bash
set -euo pipefail

REPO=https://github.com/mohinxhuw/-.git
BRANCH=${BRANCH:-ccr-4886f54a-w71o4y}
DIR=/opt/faheem

if ! command -v docker >/dev/null; then
  echo ">> Installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
command -v git >/dev/null || { apt-get update -q && apt-get install -yq git; }

if [ -d "$DIR/.git" ]; then
  echo ">> Updating code"
  git -C "$DIR" pull -q origin "$BRANCH"
else
  echo ">> Downloading code (lecture-bot folder only)"
  git clone -q --depth 1 --filter=blob:none --sparse -b "$BRANCH" "$REPO" "$DIR"
  git -C "$DIR" sparse-checkout set lecture-bot
fi
cd "$DIR/lecture-bot"

# Ask for the secrets until both look valid. Only the token/key pattern is kept,
# so pasting extra text around them (for example a whole curl example) still works.
[ -f .env ] || cp .env.example .env
chmod 600 .env
set_env() { grep -v "^$1=" .env > .env.tmp || true; printf '%s=%s\n' "$1" "$2" >> .env.tmp; mv .env.tmp .env; chmod 600 .env; }
if ! grep -qE '^TELEGRAM_BOT_TOKEN=[0-9]+:' .env; then
  while :; do
    read -rp "Telegram bot token: " IN </dev/tty
    TOKEN=$(printf '%s' "$IN" | grep -oE '[0-9]{6,}:[A-Za-z0-9_-]{30,}' | head -1 || true)
    [ -n "$TOKEN" ] && break
    echo "   That does not look like a bot token (example 123456789:AAH...). Try again."
  done
  set_env TELEGRAM_BOT_TOKEN "$TOKEN"
fi
if ! grep -qE '^ANTHROPIC_API_KEY=sk-ant-' .env; then
  while :; do
    read -rp "Anthropic API key: " IN </dev/tty
    KEY=$(printf '%s' "$IN" | grep -oE 'sk-ant-[A-Za-z0-9_-]{20,}' | head -1 || true)
    [ -n "$KEY" ] && break
    echo "   That does not look like an Anthropic key (it starts with sk-ant-). Try again."
  done
  set_env ANTHROPIC_API_KEY "$KEY"
fi

# Optional: files up to 2 GB through a self-hosted Telegram Bot API server.
if ! grep -qE '^TELEGRAM_API_ID=' .env; then
  echo
  echo "Files bigger than 20 MB need api_id and api_hash from https://my.telegram.org"
  echo "(API development tools). Press Enter to skip."
  read -rp "api_id: " API_ID </dev/tty
  API_ID=$(printf '%s' "$API_ID" | tr -cd '0-9')
  if [ -n "$API_ID" ]; then
    while :; do
      read -rp "api_hash: " IN </dev/tty
      API_HASH=$(printf '%s' "$IN" | grep -oE '[0-9a-f]{32}' | head -1 || true)
      [ -n "$API_HASH" ] && break
      echo "   api_hash is 32 letters and digits. Try again."
    done
    set_env TELEGRAM_API_HASH "$API_HASH"
    set_env TELEGRAM_LOCAL_API_URL "http://telegram-bot-api:8081"
    set_env COMPOSE_PROFILES "bigfiles"
  fi
  set_env TELEGRAM_API_ID "$API_ID"
fi

echo ">> Building and starting the bot (first build takes several minutes)"
docker compose up -d --build
echo ">> Done. Logs: cd $DIR/lecture-bot && docker compose logs -f bot"
