#!/usr/bin/env bash
# audio_volume_analysis.sh
# Hinglish: WAV file ka volume check karega, suggestion dega, aur optional amplify karega.
# Usage:
#   ./audio_volume_analysis.sh /path/to/file.wav         # analyze
#   ./audio_volume_analysis.sh -a /path/to/file.wav      # amplify (auto) and save _loud.wav
set -e
FILE="${2:-${1:-./temp_stt_input.wav}}"
DO_AMPLIFY=false
if [ "$1" = "-a" ]; then
  DO_AMPLIFY=true
  FILE="${2:-./temp_stt_input.wav}"
fi

if [ ! -f "$FILE" ]; then
  echo "File not found: $FILE"
  exit 2
fi

echo "Analyzing: $FILE"
# run ffmpeg volumedetect and extract mean_volume / max_volume
OUT=$(ffmpeg -hide_banner -nostats -i "$FILE" -af "volumedetect" -f null /dev/null 2>&1)
MEAN=$(echo "$OUT" | awk -F'mean_volume:' '/mean_volume/ {print $2}' | head -n1 | sed 's/ dB//; s/ //g')
MAX=$(echo "$OUT" | awk -F'max_volume:' '/max_volume/ {print $2}' | head -n1 | sed 's/ dB//; s/ //g')

# fallback parsing if above fails
if [ -z "$MEAN" ]; then
  MEAN=$(echo "$OUT" | grep -oP 'mean_volume:\s*-?\d+(\.\d+)? dB' | head -n1 | awk '{print $2}')
fi
if [ -z "$MAX" ]; then
  MAX=$(echo "$OUT" | grep -oP 'max_volume:\s*-?\d+(\.\d+)? dB' | head -n1 | awk '{print $2}')
fi

echo "mean_volume: ${MEAN:-N/A} dB"
echo "max_volume:  ${MAX:-N/A} dB"

# Interpret
MEAN_NUM=$(printf "%.1f" "${MEAN:--999}")
THRESH_WARN=-40.0
THRESH_BAD=-60.0

if awk "BEGIN {exit !($MEAN_NUM <= $THRESH_BAD)}"; then
  echo "Status: TOO QUIET (very low). Model likely won't detect speech."
elif awk "BEGIN {exit !($MEAN_NUM <= $THRESH_WARN)}"; then
  echo "Status: Low volume. Better to amplify or re-record louder (recommended)."
else
  echo "Status: Volume OK for STT (should work)."
fi

echo ""
echo "Suggestions:"
echo " - Agar mean_volume <= -45 dB: mic gain bad ya recording bahut halki. Re-record karen (zara loud bol ke)."
echo " - Windows: Settings → System → Sound → Input → Select mic → Device properties → Levels -> 80-100%"
echo " - Agar WSL mic forwarding problem ho: record in Windows Voice Recorder, copy .wav to WSL and test."
echo ""
if [ "$DO_AMPLIFY" = true ]; then
  OUTFILE="${FILE%.*}_loud.wav"
  echo "Amplifying and normalizing to $OUTFILE (loudnorm)... thoda time lagega..."
  ffmpeg -y -hide_banner -loglevel error -i "$FILE" -af "loudnorm=I=-16:TP=-1.5:LRA=11" "$OUTFILE"
  echo "Amplified file saved to: $OUTFILE"
  echo "Run: ./audio_volume_analysis.sh $OUTFILE  to re-check"
fi

exit 0
