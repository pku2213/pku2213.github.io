"""Build browser favicon assets from a user-provided image.

The source image is center-cropped only when it is not square. The script keeps
an optimized full-size PNG copy and creates the sizes used by desktop browsers,
high-density devices, Apple touch icons, and the legacy ``favicon.ico`` path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = PROJECT_ROOT / "site"
IMAGE_DIRECTORY = SITE_ROOT / "assets" / "img"


def resized(image: Image.Image, size: int) -> Image.Image:
    """Return a high-quality square rendition without changing the composition."""
    return ImageOps.fit(
        image,
        (size, size),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def build(source_path: Path) -> list[Path]:
    """Create all favicon files and return their output paths."""
    if not source_path.is_file():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as source:
        source.load()
        rgba = source.convert("RGBA")
        square_size = min(rgba.size)
        square = resized(rgba, square_size)

    outputs = {
        IMAGE_DIRECTORY / "favicon-source.png": square,
        IMAGE_DIRECTORY / "favicon-personal-32.png": resized(square, 32),
        IMAGE_DIRECTORY / "favicon-personal-192.png": resized(square, 192),
        IMAGE_DIRECTORY / "apple-touch-icon.png": resized(square, 180),
    }

    for output_path, image in outputs.items():
        image.save(output_path, format="PNG", optimize=True)

    ico_path = SITE_ROOT / "favicon.ico"
    square.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )

    return [*outputs, ico_path]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the new source image")
    args = parser.parse_args()

    for output_path in build(args.source.resolve()):
        relative_path = output_path.relative_to(PROJECT_ROOT)
        print(f"Created {relative_path}")


if __name__ == "__main__":
    main()
