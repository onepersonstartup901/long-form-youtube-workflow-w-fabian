#!/usr/bin/env python3
"""
Audio Enhancement for YouTube Videos.

Applies a professional voice processing chain using FFmpeg:
highpass, lowpass, EQ, compression, and loudness normalization.
"""

import subprocess
import sys
import argparse
import os


def check_ffmpeg():
    """Verify FFmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def enhance_audio(input_path: str, output_path: str, preset: str = "voice") -> bool:
    """
    Apply audio enhancement chain to a video file.

    Args:
        input_path: Input video/audio file
        output_path: Output file path
        preset: Enhancement preset (voice, music, minimal)

    Returns:
        True if successful
    """
    presets = {
        "voice": (
            "highpass=f=80,"
            "lowpass=f=12000,"
            "equalizer=f=200:t=h:w=100:g=-1,"
            "equalizer=f=3000:t=h:w=500:g=2,"
            "acompressor=threshold=-20dB:ratio=3:attack=5:release=50,"
            "loudnorm=I=-16:TP=-1.5:LRA=11"
        ),
        "music": (
            "highpass=f=30,"
            "acompressor=threshold=-25dB:ratio=2:attack=10:release=100,"
            "loudnorm=I=-14:TP=-1:LRA=13"
        ),
        "minimal": (
            "loudnorm=I=-16:TP=-1.5:LRA=11"
        ),
    }

    if preset not in presets:
        print(f"Error: Unknown preset '{preset}'. Use: {', '.join(presets.keys())}")
        return False

    audio_filter = presets[preset]

    # Check if input has video
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        input_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    has_video = "video" in result.stdout

    if has_video:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "copy",
            "-af", audio_filter,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-loglevel", "error",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", audio_filter,
            "-c:a", "aac", "-b:a", "192k",
            "-loglevel", "error",
            output_path,
        ]

    print(f"Enhancing audio ({preset} preset)...")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_path}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False

    print("Audio enhancement complete.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Enhance audio in video/audio files")
    parser.add_argument("input", help="Input video or audio file")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--preset", default="voice",
                        choices=["voice", "music", "minimal"],
                        help="Enhancement preset (default: voice)")

    args = parser.parse_args()

    if not check_ffmpeg():
        print("Error: FFmpeg not found. Install with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    success = enhance_audio(args.input, args.output, args.preset)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
