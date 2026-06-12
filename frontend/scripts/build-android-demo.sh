#!/usr/bin/env bash
# Build a debug APK wired to the public Render demo API.
# Requires Node ≥ 24.15, JDK 21+, Android SDK (ANDROID_HOME).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_ORIGIN="${MM_API_BASE_URL:-https://mentormind-api.onrender.com}"
OUT_DIR="$ROOT/../docs/releases"
APK_NAME="mentormind-demo.apk"

# Prefer Homebrew JDK 21 — Capacitor 8 / AGP reject JDK 26 for androidJdkImage.
if [[ -z "${JAVA_HOME:-}" && -d /opt/homebrew/opt/openjdk@21 ]]; then
  export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
fi
if [[ -z "${ANDROID_HOME:-}" && -d "$HOME/Library/Android/sdk" ]]; then
  export ANDROID_HOME="$HOME/Library/Android/sdk"
fi

cd "$ROOT"
export MM_API_BASE_URL="$API_ORIGIN"
npm run build:mobile

cd "$ROOT/android"
./gradlew assembleDebug

mkdir -p "$OUT_DIR"
cp app/build/outputs/apk/debug/app-debug.apk "$OUT_DIR/$APK_NAME"
echo ""
echo "✓ Demo APK → $OUT_DIR/$APK_NAME"
echo "  API origin: $API_ORIGIN"
echo "  Login: student@mentormind.dev / mentormind123"
