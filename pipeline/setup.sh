#!/usr/bin/env bash
# Installe tout ce qu'il faut pour fabriquer les vidéos (idempotent).
set -euo pipefail
pip install --break-system-packages -q piper-tts onnxruntime soundfile numpy pillow 2>&1 | grep -v -i warning || true
command -v ffmpeg >/dev/null || { echo "ffmpeg manquant"; exit 1; }
DIR="${KOKORO_DIR:-$HOME/.cache/laqlture/kokoro-multi-lang-v1_0}"
if [ ! -f "$DIR/model.onnx" ]; then
  mkdir -p "$(dirname "$DIR")"
  echo "Téléchargement de la voix Kokoro (~330 Mo)…"
  curl -sL --max-time 900 -o /tmp/kokoro.tar.bz2 \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
  tar -xjf /tmp/kokoro.tar.bz2 -C "$(dirname "$DIR")"
  rm -f /tmp/kokoro.tar.bz2
fi
python3 -c "from piper.phonemize_espeak import EspeakPhonemizer; EspeakPhonemizer().phonemize('fr','test')" >/dev/null
echo "OK : prêt à fabriquer les vidéos"
