import csv
import os
import random
import sys

def generate_test_case(index):
    a_digits = 2 * int(index // 20) + 3
    b_digits = int(a_digits * (index % 20) / 20) + 1
    a_min, a_max = 10**(a_digits - 1), 10**a_digits - 1
    b_min, b_max = 10**(b_digits - 1), 10**b_digits - 1
    
    a = random.randint(a_min, a_max)
    b = random.randint(b_min, b_max)

    return {
        "input": f"{a} {b}",
        "expected_output": str(a * b),
        "private": "true" if index % 2 == 1 else "false"
    }

def main(num_samples=100, seed=None):
    if seed is not None:
        random.seed(seed)
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'questions.csv')
    
    with open(csv_path, 'w', newline='') as csvfile:
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
