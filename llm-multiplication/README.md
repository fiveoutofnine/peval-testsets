# LLM Multiplication | Peval Competition

[**Link**](https://peval.io/competition/llm-multiplication) / [`questions.csv`](https://github.com/fiveoutofnine/peval-testsets/blob/main/llm-multiplication/questions.csv)

## Test-set design

The test-set was designed to test a wide range of randomly-generated multiplication operations from 3-digit to 13-digit. The complexity increases progressively:
- Every 20 questions, the number of digits in the first multiplicand increases by 2 (starting from 3 digits)
- Within each group of 20, the second multiplicand's digit count varies from 1 up to the same number of digits as the first multiplicand
- This creates a gradient of difficulty from simple (3-digit × 1-digit) to complex (13-digit × 13-digit) multiplications

## Generating

To generate an equivalent sample test-set, run the following:

```bash
python generate.py [num_samples] [seed]
```

### Arguments
- `num_samples` (optional): Number of test cases to generate (default: 100)
- `seed` (optional): Random seed for reproducible test generation

### Examples
```bash
# Generate default 100 test cases
python generate.py

# Generate 200 test cases
python generate.py 200

# Generate 100 test cases with seed 42 for reproducibility
python generate.py 100 42
```

The script will create a `questions.csv` file with the following columns:
- `index`: Test case index
- `input`: Two space-separated integers to multiply
- `expected_output`: The correct product
- `private`: Alternates between "false" (public) and "true" (private) for each test case
