import csv
import random
import sys

def generate_test_case(index):
    grid = [[random.randint(1, 10) for _ in range(5)] for _ in range(5)]
    numbers = [grid[0][0], grid[0][1], grid[0][2], grid[0][3], grid[0][4], grid[1][4], grid[2][4], grid[3][4], grid[4][4], grid[4][3], grid[4][2], grid[4][1], grid[4][0], grid[3][0], grid[2][0], grid[1][0], grid[1][1], grid[1][2], grid[1][3], grid[2][3], grid[3][3], grid[3][2], grid[3][1], grid[2][1], grid[2][2]]
    print(len(numbers))

    return {
        "input": '\n'.join(' '.join(map(str, row)) for row in grid),
        "expected_output": ' '.join(map(str, numbers)),
        "private": "true" if index >= 20 else "false"
    }

def main(num_samples=100, seed=None):
    if seed is not None:
        random.seed(seed)
    
    with open('questions.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['index', 'input', 'expected_output', 'private'])
        
        for i in range(num_samples):
            test_case = generate_test_case(i)
            writer.writerow([i, test_case["input"], test_case["expected_output"], test_case["private"]])
    
    print(f"Generated {num_samples} test cases in questions.csv")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        num_samples = int(sys.argv[1])
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    else:
        num_samples = 100
        seed = None
    
    main(num_samples, seed)