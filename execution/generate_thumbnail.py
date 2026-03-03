#!/usr/bin/env python3
"""
YouTube Thumbnail Generator.

Generates eye-catching 1280x720 thumbnails for YouTube videos.
Two modes: AI-generated backgrounds via Flux (Replicate) or
template-based using Pillow only (no API needed).
"""

import os
import sys
import argparse
import math
import textwrap
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# YouTube thumbnail dimensions
THUMB_WIDTH = 1280
THUMB_HEIGHT = 720

# Font search paths (macOS, Linux, Windows)
FONT_SEARCH_PATHS = [
    # macOS
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf",
    # Windows
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/ariblk.ttf",
]


def find_bold_font() -> str | None:
    """Find a suitable bold font from system paths."""
    for font_path in FONT_SEARCH_PATHS:
        if os.path.exists(font_path):
            return font_path
    return None


def extract_title_keywords(title: str, max_words: int = 5) -> str:
    """
    Extract the most impactful words from a title for thumbnail text.

    Strips common filler words and keeps the punchiest keywords.
    """
    filler_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "can", "that",
        "this", "these", "those", "it", "its", "your", "my", "our",
        "their", "his", "her", "you", "we", "they", "i",
    }

    words = title.strip().split()
    # Keep numbers and non-filler words
    keywords = [w for w in words if w.lower().strip(".,!?:;\"'") not in filler_words]

    # If too aggressive, fall back to original words
    if len(keywords) < 2:
        keywords = words

    return " ".join(keywords[:max_words]).upper()


def build_ai_prompt(title: str) -> str:
    """Build an image generation prompt from the video title."""
    return (
        f"Cinematic dramatic background for YouTube thumbnail about: {title}. "
        "Ultra wide angle, dramatic lighting, vibrant colors, "
        "professional photography style, shallow depth of field, "
        "dark moody atmosphere with accent colors, 16:9 aspect ratio, "
        "no text, no letters, no words, no watermarks."
    )


def generate_ai_background(title: str, output_path: Path) -> bool:
    """
    Generate a cinematic background image using Flux Schnell via Replicate.

    Returns True on success, False on failure.
    """
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("  REPLICATE_API_TOKEN not set, cannot generate AI background")
        return False

    try:
        import replicate
        import httpx

        prompt = build_ai_prompt(title)
        print(f"  Generating AI background...")
        print(f"  Prompt: {prompt[:100]}...")

        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "png",
                "output_quality": 95,
            },
        )

        # Output is a list of URLs or FileOutput objects
        if output:
            url = str(output[0]) if isinstance(output, list) else str(output)
            print(f"  Downloading generated image...")
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            print(f"  AI background saved to {output_path}")
            return True
        else:
            print("  Replicate returned empty output")
            return False

    except Exception as e:
        print(f"  AI background generation failed: {e}")
        return False


def create_gradient_background(width: int, height: int, colors: list[tuple] = None):
    """
    Create a gradient background image.

    Args:
        width: Image width
        height: Image height
        colors: List of (R, G, B) tuples for gradient stops.
                Defaults to dark blue -> purple.
    """
    from PIL import Image

    if colors is None:
        colors = [(10, 10, 40), (60, 10, 80), (120, 20, 60)]

    img = Image.new("RGB", (width, height))
    pixels = img.load()

    num_stops = len(colors)
    for y in range(height):
        # Calculate position in gradient (0.0 to 1.0)
        t = y / height

        # Determine which two stops we're between
        segment = t * (num_stops - 1)
        idx = min(int(segment), num_stops - 2)
        local_t = segment - idx

        # Interpolate between stops
        c1 = colors[idx]
        c2 = colors[idx + 1]
        r = int(c1[0] + (c2[0] - c1[0]) * local_t)
        g = int(c1[1] + (c2[1] - c1[1]) * local_t)
        b = int(c1[2] + (c2[2] - c1[2]) * local_t)

        for x in range(width):
            pixels[x, y] = (r, g, b)

    return img


def add_accent_elements(draw, width: int, height: int):
    """Add geometric accent elements to the template thumbnail."""
    # Top-left corner accent lines
    accent_color = (255, 200, 50, 180)  # Gold with transparency

    # Diagonal accent line top-left
    for i in range(3):
        offset = i * 15
        draw.line(
            [(0, 80 + offset), (200 - offset, 0)],
            fill=accent_color,
            width=3,
        )

    # Bottom-right corner accent lines
    for i in range(3):
        offset = i * 15
        draw.line(
            [(width, height - 80 - offset), (width - 200 + offset, height)],
            fill=accent_color,
            width=3,
        )

    # Subtle horizontal rule
    rule_y = height - 120
    draw.line(
        [(width * 0.1, rule_y), (width * 0.9, rule_y)],
        fill=(255, 255, 255, 60),
        width=2,
    )

    # Small accent rectangles
    draw.rectangle(
        [(50, height - 100), (90, height - 96)],
        fill=accent_color,
    )
    draw.rectangle(
        [(width - 90, height - 100), (width - 50, height - 96)],
        fill=accent_color,
    )


def add_gradient_overlay(img):
    """Add a semi-transparent gradient overlay for text readability."""
    from PIL import Image

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pixels = overlay.load()
    width, height = img.size

    for y in range(height):
        # Stronger overlay in the center where text goes
        # and at bottom for branding
        center_dist = abs(y - height * 0.45) / (height * 0.5)
        alpha = int(max(0, 140 - center_dist * 100))

        # Extra darkness at bottom
        if y > height * 0.75:
            bottom_t = (y - height * 0.75) / (height * 0.25)
            alpha = max(alpha, int(bottom_t * 160))

        for x in range(width):
            pixels[x, y] = (0, 0, 0, alpha)

    # Composite
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return Image.alpha_composite(img, overlay)


def render_text_with_stroke(
    draw,
    text: str,
    position: tuple,
    font,
    fill=(255, 255, 255),
    stroke_fill=(0, 0, 0),
    stroke_width: int = 4,
):
    """Render text with a dark stroke/outline for readability."""
    x, y = position
    # Draw stroke by rendering text offset in all directions
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
    # Draw main text on top
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text_to_lines(text: str, font, max_width: int, draw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def generate_thumbnail_ai(
    title: str,
    video_id: str,
    output_path: Path,
) -> Path:
    """
    Generate a thumbnail with AI-generated background.

    Falls back to template mode if AI generation fails.
    """
    from PIL import Image, ImageDraw, ImageFont

    print(f"Mode: AI-generated (Flux via Replicate)")
    print(f"Title: {title}")

    # Generate AI background
    tmp_dir = PROJECT_ROOT / ".tmp" / video_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bg_path = tmp_dir / "thumbnail_bg.png"

    ai_success = generate_ai_background(title, bg_path)

    if not ai_success:
        print("  Falling back to template mode...")
        return generate_thumbnail_template(title, video_id, output_path)

    # Load and resize AI background
    bg = Image.open(bg_path).convert("RGBA")
    bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)

    # Add gradient overlay for text readability
    print("  Adding gradient overlay...")
    img = add_gradient_overlay(bg)

    # Add text overlay
    print("  Adding text overlay...")
    draw = ImageDraw.Draw(img)

    # Find font
    font_path = find_bold_font()
    keywords = extract_title_keywords(title)
    lines = _layout_and_render_text(draw, keywords, font_path, img.size)

    # Convert to RGB for PNG save
    final = img.convert("RGB")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(str(output_path), "PNG", quality=95)
    print(f"  Thumbnail saved to {output_path}")
    print(f"  Size: {THUMB_WIDTH}x{THUMB_HEIGHT}")

    return output_path


def _layout_and_render_text(draw, keywords: str, font_path: str | None, img_size: tuple):
    """Layout and render the title text centered on the image."""
    from PIL import ImageFont

    width, height = img_size
    max_text_width = int(width * 0.85)

    # Try different font sizes to find optimal fit
    target_sizes = [96, 84, 72, 64, 56, 48]

    for font_size in target_sizes:
        try:
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default(size=font_size)
        except (OSError, TypeError):
            try:
                font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            break

        lines = wrap_text_to_lines(keywords, font, max_text_width, draw)

        # Check if lines fit vertically (leave room for margins)
        line_height = font_size * 1.3
        total_text_height = len(lines) * line_height
        if total_text_height < height * 0.5 and len(lines) <= 3:
            break

    # Calculate vertical position (centered, slightly above middle)
    total_height = len(lines) * line_height
    start_y = (height - total_height) / 2 - 20

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        y = start_y + i * line_height

        render_text_with_stroke(
            draw,
            line,
            (x, y),
            font,
            fill=(255, 255, 255),
            stroke_fill=(0, 0, 0),
            stroke_width=max(4, font_size // 16),
        )

    return lines


def generate_thumbnail_template(
    title: str,
    video_id: str,
    output_path: Path,
) -> Path:
    """
    Generate a thumbnail using only Pillow (no API needed).

    Creates a gradient background with geometric accents and bold text.
    """
    from PIL import Image, ImageDraw, ImageFont

    print(f"Mode: Template-based (Pillow only)")
    print(f"Title: {title}")

    # Create gradient background
    print("  Creating gradient background...")
    img = create_gradient_background(THUMB_WIDTH, THUMB_HEIGHT)
    img = img.convert("RGBA")

    # Add accent elements
    print("  Adding accent elements...")
    draw = ImageDraw.Draw(img, "RGBA")
    add_accent_elements(draw, THUMB_WIDTH, THUMB_HEIGHT)

    # Add a subtle radial glow in the center
    glow = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    glow_pixels = glow.load()
    cx, cy = THUMB_WIDTH // 2, THUMB_HEIGHT // 2 - 40
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    for y in range(THUMB_HEIGHT):
        for x in range(THUMB_WIDTH):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = dist / max_dist
            alpha = int(max(0, 40 * (1 - t * t)))
            glow_pixels[x, y] = (100, 60, 200, alpha)
    img = Image.alpha_composite(img, glow)

    # Draw text
    print("  Rendering title text...")
    draw = ImageDraw.Draw(img, "RGBA")
    font_path = find_bold_font()
    keywords = extract_title_keywords(title)
    _layout_and_render_text(draw, keywords, font_path, img.size)

    # Add branding bar at bottom
    bar_height = 60
    bar = Image.new("RGBA", (THUMB_WIDTH, bar_height), (0, 0, 0, 120))
    img.paste(bar, (0, THUMB_HEIGHT - bar_height), bar)

    # Convert to RGB for PNG save
    final = img.convert("RGB")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(str(output_path), "PNG", quality=95)
    print(f"  Thumbnail saved to {output_path}")
    print(f"  Size: {THUMB_WIDTH}x{THUMB_HEIGHT}")

    return output_path


def generate_thumbnail(
    title: str,
    video_id: str,
    mode: str = "template",
    output: str = None,
) -> Path:
    """
    Main entry point for thumbnail generation.

    Args:
        title: Video title or topic
        video_id: Unique video identifier
        mode: 'ai' for Flux-generated background, 'template' for Pillow-only
        output: Output file path (default: .tmp/{video_id}/thumbnail.png)

    Returns:
        Path to the generated thumbnail
    """
    if output:
        output_path = Path(output)
    else:
        output_path = PROJECT_ROOT / ".tmp" / video_id / "thumbnail.png"

    print(f"\n--- Thumbnail Generation ---")
    print(f"Video ID: {video_id}")

    if mode == "ai":
        return generate_thumbnail_ai(title, video_id, output_path)
    else:
        return generate_thumbnail_template(title, video_id, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate YouTube thumbnail (1280x720)"
    )
    parser.add_argument(
        "--video-id",
        required=True,
        help="Unique video identifier (e.g. 20260303_ai_tools)",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Video title or topic for the thumbnail",
    )
    parser.add_argument(
        "--mode",
        choices=["ai", "template"],
        default="template",
        help="Generation mode: 'ai' (Flux via Replicate) or 'template' (Pillow only). Default: template",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: .tmp/{video_id}/thumbnail.png)",
    )

    args = parser.parse_args()

    result = generate_thumbnail(
        title=args.title,
        video_id=args.video_id,
        mode=args.mode,
        output=args.output,
    )

    print(f"\nDone! Thumbnail: {result}")


if __name__ == "__main__":
    main()
