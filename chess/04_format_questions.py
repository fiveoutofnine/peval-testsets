#!/usr/bin/env python3
"""Convert positions.csv to questions.csv in competition format"""
import csv
import sys
import os

def main():
    if not os.path.exists("positions.csv"):
        print("Error: positions.csv not found. Run 03_select_simple.py first.", file=sys.stderr)
        sys.exit(1)
    
    # Read positions
    positions = []
    with open("positions.csv", 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            positions.append(row)
    
    # Convert to competition format
    # Format: index, input, expected_output, private
    with open("questions.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["index", "input", "expected_output", "private"])
        
        for i, pos in enumerate(positions):
            # Input is the FEN position
            input_str = pos['fen']
            
            # Expected output would be the best move from Stockfish analysis
            # For now, placeholder - will need powerful Stockfish instance
            expected_output = ""  # TODO: Run Stockfish analysis
            
            # Private flag based on hash_bucket
            # Use 80/20 split: bucket >= 80 is private (20% of data)
            private = pos['hash_bucket'] >= '80'  # String comparison since CSV values are strings
            
            writer.writerow([i, input_str, expected_output, private])
    
    print(f"Created questions.csv with {len(positions)} positions")
    print(f"- Public: {sum(1 for p in positions if int(p['hash_bucket']) < 80)}")
    print(f"- Private: {sum(1 for p in positions if int(p['hash_bucket']) >= 80)}")
    print("\nNote: expected_output field is empty - needs Stockfish analysis")

if __name__ == "__main__":
    main()