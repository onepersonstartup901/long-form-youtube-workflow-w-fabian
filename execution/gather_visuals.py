#!/usr/bin/env python3
"""
Visual Asset Gatherer.

Fetches stock footage/images from Pexels/Pixabay and generates
AI images via Replicate (Flux) based on script block visual directions.
"""

import os
import sys
import json
import argparse
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

# Preferred dimensions for YouTube 1080p
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080


def search_pexels_videos(query: str, per_page: int = 5) -> list[dict]:
    """Search Pexels for stock videos."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "large",
    }

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for video in data.get("videos", []):
            # Find best HD file
            best = None
            for vf in video.get("video_files", []):
                if vf.get("width", 0) >= 1280 and vf.get("quality") == "hd":
                    best = vf
                    break
            if not best:
                # Fallback to any available file
                files = video.get("video_files", [])
                if files:
                    best = max(files, key=lambda f: f.get("width", 0))

            if best:
                results.append({
                    "type": "video",
                    "source": "pexels",
                    "url": best["link"],
                    "width": best.get("width", 0),
                    "height": best.get("height", 0),
                    "duration": video.get("duration", 0),
                    "query": query,
                })

        return results
    except Exception as e:
        print(f"  Pexels search failed for '{query}': {e}")
        return []


def search_pexels_photos(query: str, per_page: int = 5) -> list[dict]:
    """Search Pexels for stock photos."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "landscape",
        "size": "large",
    }

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            results.append({
                "type": "image",
                "source": "pexels",
                "url": src.get("large2x") or src.get("large") or src.get("original"),
                "width": photo.get("width", 0),
                "height": photo.get("height", 0),
                "query": query,
            })

        return results
    except Exception as e:
        print(f"  Pexels photo search failed for '{query}': {e}")
        return []


def search_pixabay(query: str, media_type: str = "video", per_page: int = 5) -> list[dict]:
    """Search Pixabay for stock videos or images."""
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        return []

    if media_type == "video":
        url = "https://pixabay.com/api/videos/"
    else:
        url = "https://pixabay.com/api/"

    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page,
        "orientation": "horizontal",
        "min_width": 1280,
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for hit in data.get("hits", []):
            if media_type == "video":
                videos = hit.get("videos", {})
                large = videos.get("large", {}) or videos.get("medium", {})
                if large:
                    results.append({
                        "type": "video",
                        "source": "pixabay",
                        "url": large.get("url", ""),
                        "width": large.get("width", 0),
                        "height": large.get("height", 0),
                        "duration": hit.get("duration", 0),
                        "query": query,
                    })
            else:
                results.append({
                    "type": "image",
                    "source": "pixabay",
                    "url": hit.get("largeImageURL", ""),
                    "width": hit.get("imageWidth", 0),
                    "height": hit.get("imageHeight", 0),
                    "query": query,
                })

        return results
    except Exception as e:
        print(f"  Pixabay search failed for '{query}': {e}")
        return []


def generate_ai_image(prompt: str, output_path: str) -> bool:
    """Generate an AI image using Replicate (Flux)."""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("  REPLICATE_API_TOKEN not set, skipping AI image generation")
        return False

    try:
        import replicate

        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "png",
                "output_quality": 90,
            },
        )

        # Output is a list of URLs or FileOutput objects
        if output:
            url = str(output[0]) if isinstance(output, list) else str(output)
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True

    except Exception as e:
        print(f"  AI image generation failed: {e}")

    return False


def download_file(url: str, output_path: str) -> bool:
    """Download a file from URL."""
    try:
        with httpx.stream("GET", url, timeout=30, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


def gather_visuals(
    blocks: list[dict],
    output_dir: str,
    prefer_video: bool = True,
    skip_ai: bool = False,
) -> list[dict]:
    """
    Gather visual assets for all script blocks.

    Args:
        blocks: Parsed script blocks with visual_type, visual_query/visual_prompt
        output_dir: Directory to save downloaded assets
        prefer_video: Prefer stock video over images when available
        skip_ai: Skip AI image generation (use stock fallback instead)

    Returns:
        Manifest list mapping each block to its visual file
    """
    visuals_dir = os.path.join(output_dir, "visuals")
    os.makedirs(visuals_dir, exist_ok=True)

    manifest = []

    for i, block in enumerate(blocks):
        visual_type = block.get("visual_type", "stock_footage")
        visual_query = block.get("visual_query", "")
        visual_prompt = block.get("visual_prompt", "")
        block_idx = block.get("index", i)

        print(f"  Block {block_idx}: {visual_type}")

        entry = {
            "block_index": block_idx,
            "visual_type": visual_type,
            "file_path": None,
            "file_type": None,
            "source": None,
        }

        if visual_type == "ai_generated" and visual_prompt and not skip_ai:
            # Generate AI image
            filename = f"block_{block_idx:03d}_ai.png"
            filepath = os.path.join(visuals_dir, filename)

            if generate_ai_image(visual_prompt, filepath):
                entry["file_path"] = filepath
                entry["file_type"] = "image"
                entry["source"] = "flux"
                print(f"    Generated: {filename}")
            else:
                # Fallback to stock search using prompt keywords
                fallback_query = " ".join(visual_prompt.split()[:5])
                print(f"    AI failed, falling back to stock: '{fallback_query}'")
                visual_query = fallback_query
                visual_type = "stock_footage"

        if visual_type == "stock_footage" or (visual_type == "ai_generated" and not entry["file_path"]):
            query = visual_query or visual_prompt or "technology abstract"

            # Search for stock footage
            results = []
            if prefer_video:
                results = search_pexels_videos(query, per_page=3)
                if not results:
                    results = search_pixabay(query, media_type="video", per_page=3)

            # Fallback to images
            if not results:
                results = search_pexels_photos(query, per_page=3)
                if not results:
                    results = search_pixabay(query, media_type="photo", per_page=3)

            if results:
                best = results[0]
                ext = "mp4" if best["type"] == "video" else "jpg"
                filename = f"block_{block_idx:03d}_stock.{ext}"
                filepath = os.path.join(visuals_dir, filename)

                if download_file(best["url"], filepath):
                    entry["file_path"] = filepath
                    entry["file_type"] = best["type"]
                    entry["source"] = best["source"]
                    print(f"    Downloaded: {filename} ({best['source']})")
                else:
                    print(f"    Failed to download stock asset")
            else:
                print(f"    No stock results for '{query}'")

        manifest.append(entry)

        # Rate limit: be nice to APIs
        time.sleep(0.5)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Gather visual assets for script")
    parser.add_argument("script_json", help="Path to parsed script JSON")
    parser.add_argument("--output-dir", "-o", default=".tmp/video",
                        help="Output directory (default: .tmp/video)")
    parser.add_argument("--prefer-images", action="store_true",
                        help="Prefer stock images over video clips")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Skip AI image generation, use stock fallback")

    args = parser.parse_args()

    with open(args.script_json, "r") as f:
        parsed = json.load(f)

    blocks = parsed.get("blocks", [])
    if not blocks:
        print("Error: No blocks found in parsed script", file=sys.stderr)
        sys.exit(1)

    print(f"Gathering visuals for {len(blocks)} blocks...")
    manifest = gather_visuals(
        blocks=blocks,
        output_dir=args.output_dir,
        prefer_video=not args.prefer_images,
        skip_ai=args.skip_ai,
    )

    # Save manifest
    manifest_path = os.path.join(args.output_dir, "visuals_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")

    # Summary
    sourced = sum(1 for m in manifest if m["file_path"])
    missing = sum(1 for m in manifest if not m["file_path"])
    print(f"  Sourced: {sourced}/{len(manifest)}")
    if missing:
        print(f"  Missing: {missing} (will use placeholder)")


if __name__ == "__main__":
    main()
