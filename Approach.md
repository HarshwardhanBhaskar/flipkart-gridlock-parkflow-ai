# Flipkart Gridlock Hackathon 2.0: Traffic Demand Prediction Approach

## **1. Executive Summary**
Our solution addresses the core logistical challenge of predicting travel and traffic demand (`demand`) at any given location (`geohash`) and time (`timestamp`, `day`). By converting alphanumeric spatial codes into continuous coordinates, encoding cyclic temporal dynamics, and training a weighted blend of state-of-the-art Gradient Boosted Decision Trees (GBDTs), we establish a highly accurate and explainable model.

---

## **2. Robust Validation Strategy**
To ensure that our local evaluation results are completely aligned with the hackathon's public/private leaderboard metrics:
*   We implemented a **5-Fold Cross-Validation (CV)** scheme with random shuffling.
*   This validation structure ensures that every single training record receives a leakage-free validation prediction (Out-of-Fold, or OOF prediction).
*   Our local CV $R^2$ score serves as our ground truth for model tuning and selection, eliminating the risk of overfitting.

---

## **3. Advanced Feature Engineering Suite**
The raw features are significantly enriched using domain-specific transformations:

### **A. Spatial Engineering (Geohash Decoding & Clustering)**
*   **Geohash Decoding:** Alphanumeric geohashes (e.g., `qp02z1`) are high-cardinality categorical variables that trees cannot naturally parse as spatial coordinates. We implemented a fast, pure-Python Base32 geohash decoder that translates strings into numeric **Latitude and Longitude** floats.
*   **K-Means Spatial Clustering:** We apply unsupervised K-Means clustering ($K=15$) on the coordinates. This clusters locations into "traffic hotspots" and "neighborhood zones" (e.g., commercial centers, residential areas, transit nodes).
*   **Out-of-Fold Geohash Baseline Demand:** We compute the average historical traffic demand per geohash and spatial cluster. To completely avoid target leakage, this is computed out-of-fold during training, with global training averages mapped to unseen test locations.

### **B. Temporal Cyclic Encoding**
*   **Trigonometric Hour Encoding:** Representing time (from `timestamp`) linearly (e.g. 0 to 23.75) conceals the continuous cycle of a day (hour 23 is immediately adjacent to hour 0). We transformed the fractional hour into sine and cosine components:
    $$\text{hour\_sin} = \sin\left(\frac{2\pi \times \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \times \text{hour}}{24}\right)$$
*   **Weekly Trigonometric Encoding:** Similarly, the day index was converted to a cyclic day-of-week representation using $\sin(2\pi \times d / 7)$ and $\cos(2\pi \times d / 7)$.
*   **Logistical Hotspots:** Binary indicators like `is_rush_hour` (peak commute times: 8:00–10:00 AM, 5:00–8:00 PM) and `is_night` (10:00 PM–5:00 AM) were added to explicitly guide tree splits.

### **C. Environmental & Infrastructure Features**
*   **Lanes-to-Vehicles:** We combined `NumberofLanes` and `LargeVehicles` (permitted/not permitted) to calculate carrying capacities.
*   **Thermal Comfort Index:** Interaction feature mapping `Temperature * NumberofLanes` to capture environmental impact on specific roads.

---

## **4. Data Cleaning & Imputation**
*   **Missing Categoricals:** Missing fields in `RoadType`, `Weather`, `LargeVehicles`, and `Landmarks` were imputed with a descriptive `'Unknown'` placeholder category or mapped to standard modes.
*   **Missing Temperatures:** Missing `Temperature` float values were imputed dynamically using the median temperature of that specific `day` and `Weather` condition. Residual gaps were filled with the global dataset median.
*   **Encoding:** High-cardinality values were Ordinal Encoded, and bin categoricals were mapped to `1`/`0`.

---

## **5. High-Performance Ensemble Architecture**
Instead of relying on a single model, we trained three state-of-the-art Gradient Boosting algorithms that learn distinct tabular representations:
1.  **LightGBM Regressor:** Highly efficient, leaf-wise growth that excels at isolating sharp boundaries in dense numerical tables.
2.  **XGBoost Regressor:** Utilizes advanced L1 and L2 regularization to control model complexity and prevent overfitting.
3.  **CatBoost Regressor:** Natively handles categorical relationships (especially spatial clusters and road types) and implements ordered boosting to minimize variance.

### **Optimal Weighted Blending**
We collected the OOF forecasts for each algorithm and executed a grid search to maximize the composite $R^2$ score. The blended prediction is a weighted average of the models:
$$\hat{y}_{\text{final}} = w_{\text{LGB}} \hat{y}_{\text{LGB}} + w_{\text{XGB}} \hat{y}_{\text{XGB}} + w_{\text{CAT}} \hat{y}_{\text{CAT}}$$
Predictions were clipped at a lower bound of `0.0` since traffic demand cannot mathematically be negative.

---

## **6. Explaining the Model (SHAP Values)**
To ensure our predictions are interpretable and production-ready:
*   We leveraged **SHAP (SHapley Additive exPlanations)**.
*   SHAP summary plots show that `geohash_mean_demand` (our historical location baseline) and the cyclic `hour_cos`/`hour_sin` features are the strongest drivers of demand, proving our engineered features are mathematically highly significant.

---

## **7. Supply Chain Business Impact for Flipkart**
This predictive model generates substantial business value:
*   **Fleet Pre-staging:** Dispatching delivery agents to areas with high upcoming demand *before* congestion spikes, reducing average delivery times.
*   **Dynamic Delivery Slotting:** Adjusting delivery slot availability or dynamic fees during peak gridlock periods to distribute logistical loads.
*   **Eco-routing:** Designing route guidelines that steer vehicles away from geohashes during high-predicted traffic hours, saving fuel and reducing emissions.
