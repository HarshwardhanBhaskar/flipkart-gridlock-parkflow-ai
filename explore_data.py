import pandas as pd
import numpy as np

train = pd.read_csv(r"c:\Users\hwbha\c++ code\ml project\data\dataset\train.csv")
test = pd.read_csv(r"c:\Users\hwbha\c++ code\ml project\data\dataset\test.csv")

print("=== DEMAND DISTRIBUTION ===")
print(train['demand'].describe())
print(f"\nSkewness: {train['demand'].skew():.4f}")
print(f"Kurtosis: {train['demand'].kurtosis():.4f}")

print(f"\nUnique geohashes in train: {train['geohash'].nunique()}")
print(f"Unique geohashes in test: {test['geohash'].nunique()}")
test_only = set(test['geohash'].unique()) - set(train['geohash'].unique())
print(f"Geohashes in test but NOT in train: {len(test_only)}")

print(f"\nUnique days in train: {train['day'].nunique()}, range: {train['day'].min()} to {train['day'].max()}")
print(f"Unique days in test: {test['day'].nunique()}, range: {test['day'].min()} to {test['day'].max()}")
test_only_days = set(test['day'].unique()) - set(train['day'].unique())
print(f"Days in test but NOT in train: {test_only_days}")

print(f"\nUnique timestamps: {train['timestamp'].nunique()}")
print(f"\nRoadType values: {train['RoadType'].value_counts().to_dict()}")
print(f"\nWeather values: {train['Weather'].value_counts().to_dict()}")

print(f"\nGeohash prefix counts (first 4 chars):")
print(train['geohash'].str[:4].value_counts().head(10))

print(f"\n=== DEMAND BY HOUR ===")
train['hour'] = train['timestamp'].apply(lambda x: int(str(x).split(':')[0]) if ':' in str(x) else 0)
hourly = train.groupby('hour')['demand'].agg(['mean', 'std', 'count'])
print(hourly.sort_values('mean', ascending=False).head(10))

print(f"\n=== RECORDS PER GEOHASH ===")
geo_counts = train['geohash'].value_counts()
print(f"Min records per geohash: {geo_counts.min()}")
print(f"Max records per geohash: {geo_counts.max()}")
print(f"Mean records per geohash: {geo_counts.mean():.1f}")
print(f"Geohashes with < 10 records: {(geo_counts < 10).sum()}")
print(f"Geohashes with < 50 records: {(geo_counts < 50).sum()}")

print(f"\n=== MISSING VALUES ===")
print(train.isnull().sum())
print(f"\nTest missing:")
print(test.isnull().sum())

print(f"\n=== DEMAND PERCENTILES ===")
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  {p}th percentile: {np.percentile(train['demand'], p):.6f}")
