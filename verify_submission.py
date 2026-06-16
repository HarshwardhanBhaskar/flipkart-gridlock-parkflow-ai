import pandas as pd
import os

print("=" * 60)
print("FINAL PRE-SUBMISSION VERIFICATION")
print("=" * 60)

data_dir = r"c:\Users\hwbha\c++ code\ml project\data\dataset"
results_dir = r"c:\Users\hwbha\c++ code\ml project\results"

# 1. Check submission.csv
print("\n--- 1. SUBMISSION.CSV CHECK ---")
sub_path = os.path.join(results_dir, "submission.csv")
if os.path.exists(sub_path):
    sub = pd.read_csv(sub_path)
    print(f"  [OK] File exists at: {sub_path}")
    print(f"  Shape: {sub.shape}")
    print(f"  Columns: {list(sub.columns)}")
    print(f"  Null values: {sub.isnull().sum().sum()}")
    print(f"  Demand min: {sub['demand'].min():.6f}")
    print(f"  Demand max: {sub['demand'].max():.6f}")
    print(f"  Demand mean: {sub['demand'].mean():.6f}")
    
    # Check against sample_submission
    sample = pd.read_csv(os.path.join(data_dir, "sample_submission.csv"))
    print(f"\n  Sample submission columns: {list(sample.columns)}")
    print(f"  Column names match: {list(sub.columns) == list(sample.columns)}")
    
    # Check against test.csv
    test = pd.read_csv(os.path.join(data_dir, "test.csv"))
    print(f"  Row count matches test ({len(test)}): {len(sub) == len(test)}")
    print(f"  Index values match test: {sorted(sub['Index'].tolist()) == sorted(test['Index'].tolist())}")
    
    # Check row count is exactly 41778
    if sub.shape == (41778, 2):
        print("  [PASS] Shape is exactly (41778, 2) as required!")
    else:
        print(f"  [FAIL] Expected (41778, 2), got {sub.shape}")
    
    # Check no negative demand
    if sub['demand'].min() >= 0:
        print("  [PASS] All demand values are non-negative!")
    else:
        print("  [FAIL] Found negative demand values!")
    
    print(f"\n  First 5 rows of submission:")
    print(sub.head().to_string(index=False))
else:
    print(f"  [FAIL] File NOT found at: {sub_path}")

# 2. Check Jupyter Notebook
print("\n--- 2. JUPYTER NOTEBOOK CHECK ---")
nb_path = r"c:\Users\hwbha\c++ code\ml project\Traffic_Demand_Prediction_Submission.ipynb"
if os.path.exists(nb_path):
    size_kb = os.path.getsize(nb_path) / 1024
    print(f"  [OK] Notebook exists at: {nb_path}")
    print(f"  File size: {size_kb:.1f} KB")
else:
    print(f"  [FAIL] Notebook NOT found!")

# 3. Check Approach.md
print("\n--- 3. APPROACH.MD CHECK ---")
approach_path = r"c:\Users\hwbha\c++ code\ml project\Approach.md"
if os.path.exists(approach_path):
    size_kb = os.path.getsize(approach_path) / 1024
    with open(approach_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"  [OK] Approach.md exists at: {approach_path}")
    print(f"  File size: {size_kb:.1f} KB")
    print(f"  Total lines: {len(lines)}")
else:
    print(f"  [FAIL] Approach.md NOT found!")

# 4. Check train_pipeline.py
print("\n--- 4. TRAIN_PIPELINE.PY CHECK ---")
pipeline_path = r"c:\Users\hwbha\c++ code\ml project\training\train_pipeline.py"
if os.path.exists(pipeline_path):
    size_kb = os.path.getsize(pipeline_path) / 1024
    with open(pipeline_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    print(f"  [OK] Pipeline script exists at: {pipeline_path}")
    print(f"  File size: {size_kb:.1f} KB")
    print(f"  Total lines: {len(lines)}")
else:
    print(f"  [FAIL] Pipeline script NOT found!")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
