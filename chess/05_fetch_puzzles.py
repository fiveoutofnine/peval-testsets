#!/usr/bin/env python3
"""
Fetches the Lichess puzzle database.
Downloads and decompresses the full puzzle CSV file.
"""

import os
import subprocess
import sys

# Configuration
URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
OUTPUT_FILE = "output/lichess_puzzles.csv"
TEMP_FILE = "output/lichess_puzzles.csv.zst"


def download_puzzles():
    """Download and decompress the Lichess puzzle database."""
    print(f"Fetching Lichess puzzle database...")
    print(f"URL: {URL}")
    print(f"Output file: {OUTPUT_FILE}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Ensure output directory exists
    os.makedirs(os.path.join(script_dir, "output"), exist_ok=True)

    output_path = os.path.join(script_dir, OUTPUT_FILE)
    temp_path = os.path.join(script_dir, TEMP_FILE)

    try:
        # First, check if zstd is available
        subprocess.run(["zstd", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: zstd is not installed. Please install it first:")
        print("  macOS: brew install zstd")
        print("  Ubuntu/Debian: sudo apt-get install zstd")
        print("  Other: https://github.com/facebook/zstd")
        sys.exit(1)

    try:
        # Download the compressed file
        print("\nDownloading compressed puzzle database...")
        print("Note: This file is approximately 250MB compressed, ~1GB uncompressed")
        print("Download may take several minutes depending on your connection...")

        subprocess.run(
            ["curl", "-L", "--progress-bar", "-o", temp_path, URL], check=True
        )

        # Get compressed file size
        compressed_size = os.path.getsize(temp_path)
        print(f"\nDownloaded: {compressed_size / (1024 * 1024):.1f} MB (compressed)")

        # Decompress the file
        print("\nDecompressing...")
        subprocess.run(
            ["zstd", "-d", temp_path, "-o", output_path, "--force"], check=True
        )

        # Remove the compressed file
        os.remove(temp_path)

        # Check final file
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"\nSuccessfully downloaded and decompressed to {output_path}")
            print(f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")

            # Validate CSV format
            with open(output_path, encoding="utf-8", errors="ignore") as f:
                first_line = f.readline().strip()
                if "PuzzleId" in first_line or "," in first_line:
                    print("✓ File appears to contain valid CSV data")

                    # Count total lines for info
                    f.seek(0)
                    line_count = sum(1 for _ in f)
                    print(f"✓ Total puzzles: {line_count - 1:,}")  # Subtract header
                else:
                    print("⚠ Warning: File may not be in expected CSV format")
                    print(f"First line: {first_line[:100]}...")
        else:
            print("Error: Output file was not created")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"\nError during download/decompression: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
        # Clean up files
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    download_puzzles()


if __name__ == "__main__":
    main()
