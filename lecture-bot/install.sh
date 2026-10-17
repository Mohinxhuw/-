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

if [ ! -f .env ]; then
  read -rp "Telegram bot token: " TOKEN </dev/tty
  read -rp "Anthropic API key: " KEY </dev/tty
  cp .env.example .env
  sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TOKEN|; s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$KEY|" .env
  chmod 600 .env
fi

echo ">> Building and starting the bot (first build takes several minutes)"
docker compose up -d --build
echo ">> Done. Logs: cd $DIR/lecture-bot && docker compose logs -f bot"
