import os
import numpy as np
import pandas as pd
import warnings
from sklearn.model_selection import KFold
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostRegressor

warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# 1. Geohash Decoding to Coordinates
# ---------------------------------------------------------
def decode_geohash(geohash):
    """
    Decodes a geohash string into latitude and longitude floats.
    Pure python implementation without any external dependencies.
    """
    if not isinstance(geohash, str) or len(geohash) == 0:
        return np.nan, np.nan
    
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    char_to_val = {char: i for i, char in enumerate(BASE32)}
    
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    
    is_even = True
    for char in geohash.lower():
        if char not in char_to_val:
            return np.nan, np.nan
        val = char_to_val[char]
        for mask in [16, 8, 4, 2, 1]:
            bit = 1 if (val & mask) else 0
            if is_even:
                # Longitude bit
                mid = (lon_interval[0] + lon_interval[1]) / 2.0
                if bit == 1:
                    lon_interval[0] = mid
                else:
                    lon_interval[1] = mid
            else:
                # Latitude bit
                mid = (lat_interval[0] + lat_interval[1]) / 2.0
                if bit == 1:
                    lat_interval[0] = mid
                else:
                    lat_interval[1] = mid
            is_even = not is_even
            
    lat = (lat_interval[0] + lat_interval[1]) / 2.0
    lon = (lon_interval[0] + lon_interval[1]) / 2.0
    return lat, lon

# ---------------------------------------------------------
# 2. Main Training & Feature Engineering Pipeline
# ---------------------------------------------------------
def main():
    print("=" * 60)
    print("Starting Flipkart Gridlock Hackathon 2.0 ML Pipeline")
    print("=" * 60)
    
    # Define paths
    data_dir = r"c:\Users\hwbha\c++ code\ml project\data\dataset"
    models_dir = r"c:\Users\hwbha\c++ code\ml project\models"
    results_dir = r"c:\Users\hwbha\c++ code\ml project\results"
    
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    train_path = os.path.join(data_dir, "train.csv")
    test_path = os.path.join(data_dir, "test.csv")
    
    print(f"Loading datasets...")
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    
    print(f"Train Shape: {train.shape}")
    print(f"Test Shape: {test.shape}")
    
    # Save test index for final submission
    test_idx = test['Index'].copy()
    
    # Combine for uniform feature engineering
    df = pd.concat([train.drop(columns=['demand'], errors='ignore'), test], ignore_index=True)
    
    print("\n[Step 1] Spatial Feature Engineering (Geohash Decoding & Clustering)...")
    # Decode geohashes
    coords = df['geohash'].apply(decode_geohash)
    df['latitude'] = [c[0] for c in coords]
    df['longitude'] = [c[1] for c in coords]
    
    # Impute missing coordinates if any (using spatial mean)
    df['latitude'] = df['latitude'].fillna(df['latitude'].mean())
    df['longitude'] = df['longitude'].fillna(df['longitude'].mean())
    
    # K-Means clustering for location grouping
    print("Performing K-Means Clustering on location coordinates...")
    kmeans = KMeans(n_clusters=15, random_state=42, n_init=10)
    df['spatial_cluster'] = kmeans.fit_predict(df[['latitude', 'longitude']])
    
    print("\n[Step 2] Temporal Feature Engineering...")
    # Parse timestamp into numerical hour and minute
    def parse_time(t_str):
        if not isinstance(t_str, str) or ':' not in t_str:
            return 12.0 # Default fallback to noon
        h, m = map(int, t_str.split(':'))
        return h + m / 60.0
        
    df['hour'] = df['timestamp'].apply(parse_time)
    
    # Cyclic hour encoding (sine/cosine)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24.0)
    
    # Day-based features
    df['day_of_week'] = df['day'] % 7
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7.0)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7.0)
    
    # Categorize time of day
    df['is_rush_hour'] = (((df['hour'] >= 8.0) & (df['hour'] <= 10.0)) | 
                          ((df['hour'] >= 17.0) & (df['hour'] <= 20.0))).astype(int)
    df['is_night'] = ((df['hour'] >= 22.0) | (df['hour'] <= 5.0)).astype(int)
    
    print("\n[Step 3] Handling Categorical & Missing Values...")
    # Fill categorical missing values
    df['RoadType'] = df['RoadType'].fillna('Unknown')
    df['Weather'] = df['Weather'].fillna('Unknown')
    df['LargeVehicles'] = df['LargeVehicles'].fillna('Not Allowed')
    df['Landmarks'] = df['Landmarks'].fillna('No')
    
    # Map binary categoricals to numerical
    df['LargeVehicles'] = df['LargeVehicles'].map({'Allowed': 1, 'Not Allowed': 0}).fillna(0).astype(int)
    df['Landmarks'] = df['Landmarks'].map({'Yes': 1, 'No': 0}).fillna(0).astype(int)
    
    # Impute missing values for Temperature
    # Standard temp imputation by day & weather condition median
    temp_medians = df.groupby(['day', 'Weather'])['Temperature'].transform('median')
    df['Temperature'] = df['Temperature'].fillna(temp_medians)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median()) # general fallback
    
    # Impute missing values for NumberofLanes (column name verified as 'NumberofLanes' in train.csv)
    df['NumberofLanes'] = df['NumberofLanes'].fillna(df['NumberofLanes'].median())
    
    # Label encode remaining categoricals
    cat_cols = ['RoadType', 'Weather', 'geohash']
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        
    # Interaction terms
    df['temp_lanes_interaction'] = df['Temperature'] * df['NumberofLanes']
    
    # Re-split back into train and test sets
    train_feats = df.iloc[:len(train)].copy()
    test_feats = df.iloc[len(train):].copy()
    
    train_feats['demand'] = train['demand'].values
    
    print("\n[Step 4] Out-of-Fold Target Encoding (Geohash Baseline Demand)...")
    # To prevent target leakage, location stats must be computed OOF during cross-validation.
    # We will initialize columns for mean/median demand per geohash and cluster.
    train_feats['geohash_mean_demand'] = np.nan
    test_feats['geohash_mean_demand'] = np.nan
    
    # Prepare cross-validation split
    n_splits = 5
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    # Calculate geohash target stats using training folds
    global_geohash_mean = train_feats.groupby('geohash')['demand'].mean()
    global_cluster_mean = train_feats.groupby('spatial_cluster')['demand'].mean()
    global_overall_mean = train_feats['demand'].mean()
    
    for train_idx, val_idx in kf.split(train_feats):
        fold_train = train_feats.iloc[train_idx]
        
        # Calculate mean per geohash on fold training data
        fold_geohash_mean = fold_train.groupby('geohash')['demand'].mean()
        fold_cluster_mean = fold_train.groupby('spatial_cluster')['demand'].mean()
        
        # Map back to validation fold
        train_feats.iloc[val_idx, train_feats.columns.get_loc('geohash_mean_demand')] = \
            train_feats.iloc[val_idx]['geohash'].map(fold_geohash_mean).fillna(
                train_feats.iloc[val_idx]['spatial_cluster'].map(fold_cluster_mean)
            ).fillna(global_overall_mean)
            
    # For test set, map global geohash means from train set
    test_feats['geohash_mean_demand'] = test_feats['geohash'].map(global_geohash_mean).fillna(
        test_feats['spatial_cluster'].map(global_cluster_mean)
    ).fillna(global_overall_mean)
    
    # Drop index and high-cardinality temporary columns
    features_to_drop = ['Index', 'timestamp']
    X = train_feats.drop(columns=['demand'] + features_to_drop, errors='ignore')
    y = train_feats['demand']
    X_test = test_feats.drop(columns=features_to_drop, errors='ignore')
    
    feature_names = list(X.columns)
    print(f"Features used for training ({len(feature_names)}): {feature_names}")
    
    # ---------------------------------------------------------
    # 3. Model Training & Cross-Validation
    # ---------------------------------------------------------
    oof_lgb = np.zeros(len(X))
    oof_xgb = np.zeros(len(X))
    oof_cat = np.zeros(len(X))
    
    preds_lgb = np.zeros(len(X_test))
    preds_xgb = np.zeros(len(X_test))
    preds_cat = np.zeros(len(X_test))
    
    print("\n" + "="*50)
    print("Training 5-Fold Cross-Validation Ensemble")
    print("="*50)
    
    for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
        print(f"\n--- Fold {fold + 1} ---")
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        
        # --- LightGBM ---
        print("Training LightGBM model...")
        lgb_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'learning_rate': 0.05,
            'max_depth': 8,
            'num_leaves': 64,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 1,
            'verbose': -1,
            'random_state': 42
        }
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        model_lgb = lgb.train(
            lgb_params,
            train_data,
            num_boost_round=1500,
            valid_sets=[train_data, val_data],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(300)]
        )
        
        oof_lgb[val_idx] = model_lgb.predict(X_val, num_iteration=model_lgb.best_iteration)
        preds_lgb += model_lgb.predict(X_test, num_iteration=model_lgb.best_iteration) / n_splits
        
        # --- XGBoost ---
        print("Training XGBoost model...")
        model_xgb = xgb.XGBRegressor(
            n_estimators=1500,
            learning_rate=0.05,
            max_depth=7,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            early_stopping_rounds=50,
            eval_metric='rmse'
        )
        model_xgb.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=300
        )
        
        oof_xgb[val_idx] = model_xgb.predict(X_val)
        preds_xgb += model_xgb.predict(X_test) / n_splits
        
        # --- CatBoost ---
        print("Training CatBoost model...")
        model_cat = CatBoostRegressor(
            iterations=1500,
            learning_rate=0.05,
            depth=7,
            eval_metric='RMSE',
            random_seed=42,
            early_stopping_rounds=50,
            verbose=300
        )
        model_cat.fit(
            X_train, y_train,
            eval_set=(X_val, y_val),
            use_best_model=True
        )
        
        oof_cat[val_idx] = model_cat.predict(X_val)
        preds_cat += model_cat.predict(X_test) / n_splits
        
    # Calculate fold R2 scores
    print("\n" + "="*50)
    print("Cross-Validation R2 Scores")
    print("="*50)
    
    score_lgb = r2_score(y, oof_lgb)
    score_xgb = r2_score(y, oof_xgb)
    score_cat = r2_score(y, oof_cat)
    
    print(f"LightGBM OOF R2 Score : {score_lgb * 100:.4f}%")
    print(f"XGBoost  OOF R2 Score : {score_xgb * 100:.4f}%")
    print(f"CatBoost OOF R2 Score : {score_cat * 100:.4f}%")
    
    # Finding optimal blending weights
    print("\nFinding optimal blending weights...")
    best_blend_score = 0
    best_weights = (0.33, 0.33, 0.34)
    
    # Fast grid search for blending weights
    for w_lgb in np.linspace(0, 1, 21):
        for w_xgb in np.linspace(0, 1 - w_lgb, 21):
            w_cat = 1.0 - w_lgb - w_xgb
            if w_cat < 0 or w_cat > 1:
                continue
            blend_oof = w_lgb * oof_lgb + w_xgb * oof_xgb + w_cat * oof_cat
            blend_score = r2_score(y, blend_oof)
            if blend_score > best_blend_score:
                best_blend_score = blend_score
                best_weights = (w_lgb, w_xgb, w_cat)
                
    print(f"Best Ensemble Weights: LightGBM: {best_weights[0]:.2f}, XGBoost: {best_weights[1]:.2f}, CatBoost: {best_weights[2]:.2f}")
    print(f"Ensemble Blended OOF R2 Score: {best_blend_score * 100:.4f}%")
    
    # ---------------------------------------------------------
    # 4. Generate Final Submission File
    # ---------------------------------------------------------
    print("\nGenerating final submission...")
    final_preds = (best_weights[0] * preds_lgb + 
                   best_weights[1] * preds_xgb + 
                   best_weights[2] * preds_cat)
    
    # Clip predictions to valid bounds (demand cannot be negative, max in train is around 1.0)
    final_preds = np.clip(final_preds, 0.0, None)
    
    submission = pd.DataFrame({
        'Index': test_idx,
        'demand': final_preds
    })
    
    submission_path = os.path.join(results_dir, "submission.csv")
    submission.to_csv(submission_path, index=False)
    
    print(f"Submission saved to {submission_path}")
    print(f"Submission Shape: {submission.shape}")
    
    # Quick sanity checks
    print(f"Min predicted demand: {submission['demand'].min():.6f}")
    print(f"Max predicted demand: {submission['demand'].max():.6f}")
    print(f"Mean predicted demand: {submission['demand'].mean():.6f}")
    print(f"Total nulls in predictions: {submission['demand'].isnull().sum()}")
    print("=" * 60)
    print("ML Pipeline Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
