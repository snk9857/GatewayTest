from pathlib import Path
import argparse

from PIL import Image, ImageEnhance, ImageFilter


def save_image(img: Image.Image, out_dir: Path, name: str) -> None:
    out_path = out_dir / name
    img.save(out_path)
    print(f"Saved: {out_path.name}")


def center_crop(img: Image.Image, crop_percent: float) -> Image.Image:
    """
    crop_percent = percent removed from each dimension overall.
    Example: 0.10 means keep 90% of width and height.
    """
    w, h = img.size
    keep_w = int(w * (1.0 - crop_percent))
    keep_h = int(h * (1.0 - crop_percent))

    left = (w - keep_w) // 2
    top = (h - keep_h) // 2
    right = left + keep_w
    bottom = top + keep_h

    return img.crop((left, top, right, bottom)).resize((w, h), Image.Resampling.LANCZOS)


def resize_back(img: Image.Image, scale: float) -> Image.Image:
    """
    Downscale then resize back to original dimensions to simulate a legitimate resize/edit workflow.
    """
    w, h = img.size
    small_w = max(1, int(w * scale))
    small_h = max(1, int(h * scale))

    resized = img.resize((small_w, small_h), Image.Resampling.LANCZOS)
    return resized.resize((w, h), Image.Resampling.LANCZOS)


def adjust_brightness(img: Image.Image, factor: float) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(factor)


def adjust_contrast(img: Image.Image, factor: float) -> Image.Image:
    return ImageEnhance.Contrast(img).enhance(factor)


def blur_image(img: Image.Image, radius: float) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate broader usability-testing variants from one image.")
    parser.add_argument("--input", required=True, help="Path to source image")
    parser.add_argument("--out", default="usability_variants", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    base = Image.open(input_path).convert("RGB")

    # Save original too
    save_image(base, out_dir, "variant_00_original.png")

    # Brightness variants
    brightness_factors = [1.05, 1.10, 1.20, 1.30, 1.40]
    for i, factor in enumerate(brightness_factors, start=1):
        img = adjust_brightness(base, factor)
        pct = int(round((factor - 1.0) * 100))
        save_image(img, out_dir, f"variant_{i:02d}_brightness_plus_{pct}.png")

    # Contrast variants
    contrast_factors = [0.90, 1.10, 1.25]
    start_idx = 1 + len(brightness_factors)
    for j, factor in enumerate(contrast_factors, start=start_idx):
        img = adjust_contrast(base, factor)
        label = f"plus_{int(round((factor - 1.0) * 100))}" if factor >= 1 else f"minus_{int(round((1.0 - factor) * 100))}"
        save_image(img, out_dir, f"variant_{j:02d}_contrast_{label}.png")

    # Resize variants
    resize_scales = [0.90, 0.75, 0.50]
    start_idx += len(contrast_factors)
    for j, scale in enumerate(resize_scales, start=start_idx):
        img = resize_back(base, scale)
        pct = int(round(scale * 100))
        save_image(img, out_dir, f"variant_{j:02d}_resize_to_{pct}_then_back.png")

    # Crop variants
    crop_percents = [0.05, 0.10, 0.20]
    start_idx += len(resize_scales)
    for j, crop_pct in enumerate(crop_percents, start=start_idx):
        img = center_crop(base, crop_pct)
        pct = int(round(crop_pct * 100))
        save_image(img, out_dir, f"variant_{j:02d}_center_crop_{pct}.png")

    # Blur variants
    blur_radii = [0.5, 1.0, 2.0]
    start_idx += len(crop_percents)
    for j, radius in enumerate(blur_radii, start=start_idx):
        img = blur_image(base, radius)
        save_image(img, out_dir, f"variant_{j:02d}_blur_radius_{str(radius).replace('.', '_')}.png")

    print("\nDone. Generated a broader set of legitimate image variants.")


if __name__ == "__main__":
    main()