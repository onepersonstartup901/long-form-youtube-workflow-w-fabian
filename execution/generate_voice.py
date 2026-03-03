#!/usr/bin/env python3
"""
Voice Generation using ElevenLabs TTS.

Generates narration audio from parsed script blocks with word-level
timestamps for caption synchronization.
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def generate_voice(
    blocks: list[dict],
    output_dir: str,
    voice_id: str = None,
    model: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> tuple[str, list[dict]]:
    """
    Generate TTS audio from script blocks using ElevenLabs.

    Args:
        blocks: Parsed script blocks (each with 'narration' key)
        output_dir: Directory for output files
        voice_id: ElevenLabs voice ID (or from env ELEVENLABS_VOICE_ID)
        model: ElevenLabs model ID
        stability: Voice stability (0-1)
        similarity_boost: Voice similarity boost (0-1)

    Returns:
        Tuple of (combined_audio_path, word_timestamps)
    """
    from elevenlabs import ElevenLabs

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not voice_id:
        print("Error: No voice_id provided and ELEVENLABS_VOICE_ID not set", file=sys.stderr)
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)
    os.makedirs(output_dir, exist_ok=True)

    # Collect all narration text
    narrations = []
    for block in blocks:
        narration = block.get("narration", "").strip()
        if narration:
            narrations.append({
                "index": block.get("index", len(narrations)),
                "text": narration,
            })

    if not narrations:
        print("Error: No narration text found in blocks", file=sys.stderr)
        sys.exit(1)

    print(f"Generating voice for {len(narrations)} narration blocks...")
    print(f"  Voice ID: {voice_id}")
    print(f"  Model: {model}")

    # Combine all narration into one text with paragraph breaks
    # This produces more natural pacing than individual API calls
    combined_text = "\n\n".join(n["text"] for n in narrations)
    word_count = len(combined_text.split())
    print(f"  Total words: {word_count}")
    print(f"  Estimated cost: ~${len(combined_text) * 0.000030:.2f}")

    # Generate with word-level timestamps
    audio_path = os.path.join(output_dir, "narration.mp3")
    timestamps_path = os.path.join(output_dir, "word_timestamps.json")

    start_time = time.time()

    try:
        # Use the generate endpoint with timestamps
        response = client.text_to_speech.convert_with_timestamps(
            voice_id=voice_id,
            text=combined_text,
            model_id=model,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        )

        # Collect audio chunks and alignment data
        audio_chunks = []
        alignment_chars = []
        alignment_starts = []
        alignment_ends = []

        for chunk in response:
            if chunk.audio_base64:
                import base64
                audio_chunks.append(base64.b64decode(chunk.audio_base64))
            if chunk.alignment:
                alignment_chars.extend(chunk.alignment.characters)
                alignment_starts.extend(chunk.alignment.character_start_times_seconds)
                alignment_ends.extend(chunk.alignment.character_end_times_seconds)

        # Write combined audio
        with open(audio_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        # Build word-level timestamps from character alignment
        word_timestamps = _build_word_timestamps(
            alignment_chars, alignment_starts, alignment_ends
        )

        # Map words back to blocks
        _assign_blocks_to_words(word_timestamps, narrations)

        # Save timestamps
        with open(timestamps_path, "w") as f:
            json.dump(word_timestamps, f, indent=2)

        elapsed = time.time() - start_time
        print(f"  Generated in {elapsed:.1f}s")
        print(f"  Audio: {audio_path}")
        print(f"  Timestamps: {timestamps_path} ({len(word_timestamps)} words)")

        return audio_path, word_timestamps

    except Exception as e:
        # Fallback: generate without timestamps using standard endpoint
        print(f"  Timestamps API failed ({e}), falling back to standard generation...")

        response = client.text_to_speech.convert(
            voice_id=voice_id,
            text=combined_text,
            model_id=model,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        )

        with open(audio_path, "wb") as f:
            for chunk in response:
                f.write(chunk)

        # Estimate timestamps from word count and audio duration
        word_timestamps = _estimate_timestamps(combined_text, audio_path)

        with open(timestamps_path, "w") as f:
            json.dump(word_timestamps, f, indent=2)

        elapsed = time.time() - start_time
        print(f"  Generated in {elapsed:.1f}s (estimated timestamps)")
        print(f"  Audio: {audio_path}")
        print(f"  Timestamps: {timestamps_path} ({len(word_timestamps)} words)")

        return audio_path, word_timestamps


def _build_word_timestamps(
    chars: list[str], starts: list[float], ends: list[float]
) -> list[dict]:
    """Build word-level timestamps from character-level alignment."""
    words = []
    current_word = ""
    word_start = None

    for i, char in enumerate(chars):
        if char == " " or char == "\n":
            if current_word:
                words.append({
                    "word": current_word,
                    "start": word_start,
                    "end": ends[i - 1] if i > 0 else starts[i],
                })
                current_word = ""
                word_start = None
        else:
            if word_start is None:
                word_start = starts[i]
            current_word += char

    # Don't forget the last word
    if current_word and word_start is not None:
        words.append({
            "word": current_word,
            "start": word_start,
            "end": ends[-1] if ends else word_start + 0.1,
        })

    return words


def _estimate_timestamps(text: str, audio_path: str) -> list[dict]:
    """
    Estimate word timestamps when alignment data is unavailable.
    Uses uniform distribution based on audio duration.
    """
    import subprocess

    # Get audio duration
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip())

    words_list = text.split()
    if not words_list:
        return []

    time_per_word = duration / len(words_list)
    timestamps = []

    for i, word in enumerate(words_list):
        timestamps.append({
            "word": word,
            "start": round(i * time_per_word, 3),
            "end": round((i + 1) * time_per_word, 3),
        })

    return timestamps


def _assign_blocks_to_words(
    word_timestamps: list[dict], narrations: list[dict]
) -> None:
    """Assign block indices to words based on text matching."""
    word_idx = 0
    for narration in narrations:
        block_words = narration["text"].split()
        block_idx = narration["index"]

        for _ in block_words:
            if word_idx < len(word_timestamps):
                word_timestamps[word_idx]["block_index"] = block_idx
                word_idx += 1


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio from script")
    parser.add_argument("script_json", help="Path to parsed script JSON")
    parser.add_argument("--output-dir", "-o", default=".tmp/voice",
                        help="Output directory (default: .tmp/voice)")
    parser.add_argument("--voice-id", help="ElevenLabs voice ID")
    parser.add_argument("--model", default="eleven_multilingual_v2",
                        help="ElevenLabs model (default: eleven_multilingual_v2)")
    parser.add_argument("--stability", type=float, default=0.5)
    parser.add_argument("--similarity", type=float, default=0.75)

    args = parser.parse_args()

    # Load parsed script
    with open(args.script_json, "r") as f:
        parsed = json.load(f)

    blocks = parsed.get("blocks", [])
    if not blocks:
        print("Error: No blocks found in parsed script", file=sys.stderr)
        sys.exit(1)

    audio_path, timestamps = generate_voice(
        blocks=blocks,
        output_dir=args.output_dir,
        voice_id=args.voice_id,
        model=args.model,
        stability=args.stability,
        similarity_boost=args.similarity,
    )

    print(f"\nDone. Audio: {audio_path}")
    print(f"Word timestamps: {len(timestamps)} words")


if __name__ == "__main__":
    main()
