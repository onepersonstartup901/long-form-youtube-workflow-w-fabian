#!/usr/bin/env python3
"""
Final Video Export with YouTube-optimized encoding settings.

Applies encoding presets for different quality/size targets.
"""

import subprocess
import sys
import os
import argparse
import time


# Hardware encoder availability cache
_hw_available = None


def check_hardware_encoder() -> bool:
    """Check if hardware H.264 encoder is available (macOS)."""
    global _hw_available
    if _hw_available is None:
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
            )
            _hw_available = "h264_videotoolbox" in result.stdout
        except Exception:
            _hw_available = False
    return _hw_available


PRESETS = {
    "youtube_1080p": {
        "resolution": "1920:1080",
        "codec": "h264",
        "bitrate": "10M",
        "crf": "18",
        "audio_bitrate": "192k",
        "fps": 30,
    },
    "youtube_4k": {
        "resolution": "3840:2160",
        "codec": "h265",
        "bitrate": "35M",
        "crf": "18",
        "audio_bitrate": "320k",
        "fps": 30,
    },
    "draft": {
        "resolution": "1280:720",
        "codec": "h264",
        "bitrate": "5M",
        "crf": "23",
        "audio_bitrate": "128k",
        "fps": 30,
    },
}


def export_video(input_path: str, output_path: str, preset_name: str = "youtube_1080p") -> bool:
    """
    Export video with specified preset.

    Args:
        input_path: Input video file
        output_path: Output file path
        preset_name: Encoding preset name

    Returns:
        True if successful
    """
    if preset_name not in PRESETS:
        print(f"Error: Unknown preset '{preset_name}'. Available: {', '.join(PRESETS.keys())}")
        return False

    preset = PRESETS[preset_name]

    # Build encoder args
    if preset["codec"] == "h264" and check_hardware_encoder():
        encoder_args = ["-c:v", "h264_videotoolbox", "-b:v", preset["bitrate"]]
        print("Using hardware encoder (h264_videotoolbox)")
    elif preset["codec"] == "h265":
        encoder_args = ["-c:v", "libx265", "-preset", "medium", "-crf", preset["crf"], "-tag:v", "hvc1"]
        print("Using software encoder (libx265)")
    else:
        encoder_args = ["-c:v", "libx264", "-preset", "medium", "-crf", preset["crf"]]
        print("Using software encoder (libx264)")

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={preset['resolution']}:flags=lanczos",
        *encoder_args,
        "-r", str(preset["fps"]),
        "-c:a", "aac", "-b:a", preset["audio_bitrate"],
        "-movflags", "+faststart",
        "-loglevel", "error",
        "-stats",
        output_path,
    ]

    print(f"Exporting with preset: {preset_name}")
    print(f"  Resolution: {preset['resolution']}")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_path}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False

    # Get file size
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Export complete in {elapsed:.1f}s")
    print(f"  File size: {size_mb:.1f} MB")

    return True


def main():
    parser = argparse.ArgumentParser(description="Export video with YouTube-optimized settings")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--preset", default="youtube_1080p",
                        choices=list(PRESETS.keys()),
                        help="Export preset (default: youtube_1080p)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    success = export_video(args.input, args.output, args.preset)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
