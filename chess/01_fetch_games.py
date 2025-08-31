#!/usr/bin/env python3
"""
Fetches a chunk of Lichess PGN data from their database.
Downloads the full file and extracts a chunk after decompression.
"""

import os
import subprocess
import sys

# Configuration
URL = "https://database.lichess.org/standard/lichess_db_standard_rated_2025-07.pgn.zst"
CHUNK_SIZE_MB = 512  # Size of chunk to extract in MB (after decompression)
OFFSET_MB = 15_555  # Offset from start of decompressed data in MB
OUTPUT_FILE = "output/games.pgn"
TEMP_FILE = "games.pgn.zst"


def download_chunk():
    """Download a chunk of the Lichess PGN database."""
    # Convert MB to bytes
    chunk_size_bytes = CHUNK_SIZE_MB * 1024 * 1024
    offset_bytes = OFFSET_MB * 1024 * 1024

    print(f"Fetching {CHUNK_SIZE_MB}MB chunk from Lichess database...")
    print(f"URL: {URL}")
    print(f"Output file: {OUTPUT_FILE}")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Ensure output directory exists
    os.makedirs(os.path.join(script_dir, "output"), exist_ok=True)

    output_path = os.path.join(script_dir, OUTPUT_FILE)

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
        print("\nApproach: Streaming decompression with early termination")
        print(f"Will extract {CHUNK_SIZE_MB}MB starting at offset {OFFSET_MB}MB\n")

        # Use curl to stream the compressed file and pipe through zstdcat
        # Then use head/tail to extract the specific chunk
        if OFFSET_MB == 0:
            # If no offset, just use head to get the first chunk
            shell_cmd = f"curl -L --progress-bar '{URL}' | zstdcat | head -c {chunk_size_bytes} > '{output_path}'"
        else:
            # If there's an offset, we need to skip bytes first
            # Note: This will still download and decompress from the beginning
            shell_cmd = f"curl -L --progress-bar '{URL}' | zstdcat | tail -c +{offset_bytes + 1} | head -c {chunk_size_bytes} > '{output_path}'"

        print("Downloading and extracting chunk...")
        print(
            "Note: This will download/decompress from the beginning up to the desired chunk"
        )

        subprocess.run(shell_cmd, shell=True)

        # The command might return non-zero when we terminate early, which is expected
        # Check if file was created and has content
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                print(f"\nSuccessfully extracted chunk to {output_path}")
                print(
                    f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)"
                )

                # Validate that we have valid PGN data
                with open(output_path, encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("["):
                        print("✓ File appears to contain valid PGN data")
                    else:
                        print("⚠ Warning: File may not start with valid PGN data")
                        print(f"First line: {first_line[:50]}...")
            else:
                print("Error: Output file is empty")
                sys.exit(1)
        else:
            print("Error: Output file was not created")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)
    except Exception as e:
        print(f"Error during download: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    download_chunk()


if __name__ == "__main__":
    main()
