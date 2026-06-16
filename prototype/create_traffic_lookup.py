import os
import pandas as pd
import numpy as np

def parse_time(t_str):
    if not isinstance(t_str, str) or ':' not in t_str:
        return 12
    h, m = map(int, t_str.split(':'))
    return h

def main():
    print("=" * 60)
    print("CREATING BASELINE TRAFFIC DEMAND LOOKUP TABLE")
    print("=" * 60)

    train_path = r"c:\Users\hwbha\c++ code\ml project\data\dataset\train.csv"
    if not os.path.exists(train_path):
        print(f"Error: train.csv not found at {train_path}")
        return

    print("Loading train.csv...")
    df = pd.read_csv(train_path, usecols=['geohash', 'day', 'timestamp', 'demand'])
    
    print("Parsing hours and day of week...")
    df['hour'] = df['timestamp'].apply(parse_time)
    df['day_of_week'] = df['day'] % 7

    print("Aggregating demand by geohash, hour, and day of week...")
    agg_df = df.groupby(['geohash', 'hour', 'day_of_week'])['demand'].mean().reset_index()

    # Save to CSV
    os.makedirs(r"c:\Users\hwbha\c++ code\ml project\data\parking", exist_ok=True)
    out_path = r"c:\Users\hwbha\c++ code\ml project\data\parking\traffic_demand_lookup.csv"
    agg_df.to_csv(out_path, index=False)
    print(f"Traffic demand lookup table saved to {out_path}")
    print(f"Total entries: {len(agg_df)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
