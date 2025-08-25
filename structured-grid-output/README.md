# Structured Grid Output | Peval Competition

[**Link**](https://peval.io/competition/structured-grid-output) / [`questions.csv`](https://github.com/fiveoutofnine/peval-testsets/blob/main/structured-grid-output/questions.csv)

## Test-set design

For each test-case, randomly select a number $\in [1, 10]$.

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
- `input`: A 5x5 grid of space-separated integers (1-10), with rows separated by newlines
- `expected_output`: The grid values in spiral order as a single space-separated string
- `private`: "false" for first 20 test cases, "true" for the rest
