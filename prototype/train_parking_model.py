import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

# ---------------------------------------------------------
# 1. Geohash Encoder Function
# ---------------------------------------------------------
def encode_geohash(latitude, longitude, precision=6):
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    geohash = []
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    is_even = True
    while len(geohash) < precision:
        if is_even:
            mid = (lon_interval[0] + lon_interval[1]) / 2.0
            if longitude > mid:
                ch |= bits[bit]
                lon_interval[0] = mid
            else:
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2.0
            if latitude > mid:
                ch |= bits[bit]
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid
        is_even = not is_even
        if bit < 4:
            bit += 1
        else:
            geohash.append(BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)

def main():
    print("=" * 60)
    print("PROCESSING BENGALURU TRAFFIC POLICE PARKING VIOLATIONS DATASET")
    print("=" * 60)

    csv_path = r"c:\Users\hwbha\c++ code\ml project\jan to may police violation_anonymized791b166.csv"
    if not os.path.exists(csv_path):
        print(f"Error: Dataset not found at {csv_path}")
        return

    print("Loading dataset (298k+ rows)...")
    # Only load required columns to optimize memory
    cols = ['latitude', 'longitude', 'created_datetime', 'violation_type']
    df = pd.read_csv(csv_path, usecols=cols)

    print("Parsing timestamps and dates...")
    # Parse date
    df['created_datetime'] = pd.to_datetime(df['created_datetime'], format='ISO8601')
    df['hour'] = df['created_datetime'].dt.hour
    df['day_of_week'] = df['created_datetime'].dt.dayofweek

    print("Encoding coordinates into standard Geohashes of length 6...")
    # Map coordinates to geohash6
    df['geohash'] = df.apply(lambda r: encode_geohash(r['latitude'], r['longitude']), axis=1)

    print("Aggregating violations by geohash, hour, and day of week...")
    # Group by spatiotemporal buckets
    group_cols = ['geohash', 'hour', 'day_of_week']
    agg_df = df.groupby(group_cols).size().reset_index(name='violation_count')

    # Get coordinate centroids for each geohash
    centroids = df.groupby('geohash')[['latitude', 'longitude']].mean().reset_index()
    agg_df = agg_df.merge(centroids, on='geohash', how='left')

    print(f"Aggregated dataset has {len(agg_df)} unique spatiotemporal cells.")
    print(agg_df.head())

    # Save aggregated data for server use
    os.makedirs(r"c:\Users\hwbha\c++ code\ml project\data\parking", exist_ok=True)
    stats_path = r"c:\Users\hwbha\c++ code\ml project\data\parking\parking_stats.csv"
    agg_df.to_csv(stats_path, index=False)
    print(f"Aggregated statistics saved to {stats_path}")

    # Prepare features for LightGBM hotspot model
    print("\nTraining LightGBM Parking Hotspot Regressor...")
    X = agg_df[['latitude', 'longitude', 'hour', 'day_of_week']]
    y = agg_df['violation_count']

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'verbose': -1,
        'random_state': 42
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[train_data, val_data],
        callbacks=[lgb.early_stopping(50, verbose=False)]
    )

    y_pred = model.predict(X_val)
    print(f"Hotspot Regressor Validation RMSE: {np.sqrt(np.mean((y_val - y_pred)**2)):.4f}")
    print(f"Hotspot Regressor Validation R2: {r2_score(y_val, y_pred) * 100:.2f}%")

    # Save model
    model_dir = r"c:\Users\hwbha\c++ code\ml project\models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "parking_model.txt")
    model.save_model(model_path)
    print(f"Hotspot model saved to {model_path}")
    print("=" * 60)
    print("DATA PREPARATION & TRAINING COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
