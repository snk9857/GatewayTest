from PIL import Image, ImageEnhance
import argparse
from pathlib import Path

def generate_variants(input_path, output_dir):
    img = Image.open(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating variants from: {input_path}")
    print(f"Saving to: {output_dir}\n")

    for i in range(15):
        factor = 1 + (i * 0.03)  # +3% brightness each step

        enhancer = ImageEnhance.Brightness(img)
        bright_img = enhancer.enhance(factor)

        output_file = output_dir / f"variant_{i:02d}_brightness_{round((factor-1)*100,1)}.png"
        bright_img.save(output_file)

        print(f"Saved: {output_file.name} (factor={round(factor, 2)})")

    print("\n✅ Done generating brightness variants")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input image file")
    parser.add_argument("--out", default="brightness_variants", help="Output directory")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.out)

    if not input_path.exists():
        print("Error: Input file not found")
        return

    generate_variants(input_path, output_dir)

if __name__ == "__main__":
    main()