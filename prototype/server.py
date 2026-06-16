import os
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, render_template

base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static")
)

# ---------------------------------------------------------
# PATHS AND DATA LOADING
# ---------------------------------------------------------
parking_stats_path = os.path.normpath(os.path.join(base_dir, "..", "data", "parking", "parking_stats.csv"))
traffic_lookup_path = os.path.normpath(os.path.join(base_dir, "..", "data", "parking", "traffic_demand_lookup.csv"))

# Global data holders
df_parking = None
df_traffic = None
geo_mapping = {}

def load_data_and_map():
    global df_parking, df_traffic, geo_mapping
    print("Loading datasets...")
    df_parking = pd.read_csv(parking_stats_path)
    df_traffic = pd.read_csv(traffic_lookup_path)

    # 1. Rank-based Spatiotemporal Mapping (Jakarta to Bengaluru)
    # Get busiest geohashes in Bengaluru (by violation count)
    bengaluru_totals = df_parking.groupby('geohash')['violation_count'].sum().reset_index()
    bengaluru_sorted = bengaluru_totals.sort_values(by='violation_count', ascending=False)['geohash'].tolist()

    # Get busiest geohashes in Jakarta (by average demand)
    jakarta_totals = df_traffic.groupby('geohash')['demand'].mean().reset_index()
    jakarta_sorted = jakarta_totals.sort_values(by='demand', ascending=False)['geohash'].tolist()

    # Map them rank-for-rank
    for idx, bg_geo in enumerate(bengaluru_sorted):
        # Map to the corresponding rank in Jakarta (wrap around if Jakarta list is smaller)
        jk_geo = jakarta_sorted[idx % len(jakarta_sorted)]
        geo_mapping[bg_geo] = jk_geo

    print(f"Mapped {len(geo_mapping)} Bengaluru geohashes to Jakarta demand profiles.")

# Load data on start
load_data_and_map()

# ---------------------------------------------------------
# BOTTLENECK ENGINE FORMULAS (RUPESS ₹)
# ---------------------------------------------------------
def calculate_traffic_impact(violations, baseline_demand):
    # Baseline capacity is 1.0 (100% capacity)
    # Each violation blocks critical road width, reducing capacity by 7% per vehicle (max 65%)
    capacity_reduction = min(violations * 0.07, 0.65)
    remaining_capacity = max(1.0 - capacity_reduction, 0.35)

    # Congestion Drag Index (CDI) = demand / capacity
    cdi = baseline_demand / remaining_capacity

    # Estimated Delay in minutes
    delay_minutes = 15.0 * cdi

    # Targeted Enforcement Priority (TEP) = violations * CDI
    tep = violations * cdi

    # Economic Loss in Indian Rupees (₹)
    # Assumes ₹300 per hour time-value of commuters, and ~400 vehicles affected per hour
    # Economic Loss = (Delay / 60) * 400 * ₹300 = Delay * ₹2000
    economic_loss_rupees = round(delay_minutes * 2000)

    return {
        "remaining_capacity_pct": round(remaining_capacity * 100, 1),
        "cdi": round(cdi, 3),
        "delay_minutes": round(delay_minutes, 1),
        "tep": round(tep, 3),
        "economic_loss_rupees": economic_loss_rupees
    }

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hotspots', methods=['GET'])
def get_hotspots():
    hour = int(request.args.get('hour', 9))
    day_of_week = int(request.args.get('day_of_week', 0)) # 0 = Monday, 6 = Sunday

    # Filter parking violations for this specific hour and day of week
    parking_filtered = df_parking[(df_parking['hour'] == hour) & (df_parking['day_of_week'] == day_of_week)]
    
    # If no violations exist for this hour, fall back to geohash spatial centroids with 0 counts
    if len(parking_filtered) == 0:
        parking_filtered = df_parking.groupby(['geohash', 'latitude', 'longitude']).first().reset_index()
        parking_filtered['violation_count'] = 0

    hotspots = []
    
    # Pre-aggregate traffic lookup for quick query
    traffic_subset = df_traffic[(df_traffic['hour'] == hour) & (df_traffic['day_of_week'] == day_of_week)]
    traffic_lookup = dict(zip(traffic_subset['geohash'], traffic_subset['demand']))
    global_traffic_mean = df_traffic[df_traffic['hour'] == hour]['demand'].mean() if len(df_traffic[df_traffic['hour'] == hour]) > 0 else 0.1

    # Map name mapping for demo
    dummy_names = {
        "tdr1w3": "KR Puram Junction / NH 44",
        "tdr32j": "Whitefield ITPL Main Road",
        "tdr1ey": "Hebbal Flyover Access Road",
        "tdr1v6": "Kamaraj Road / Commercial Street",
        "tdr1y5": "Embassy Tech Village Entrance",
        "tdr1yj": "Marathahalli Outer Ring Road",
        "tdr1uw": "Shivaji Nagar Bus Station Cross",
        "tdr1tr": "KR Market Road (Chickpet Area)",
        "tdr1v2": "Koramangala 80ft Road / Sony World Signal",
        "tdr1vg": "Indiranagar 100 Feet Road",
        "tdr1xf": "Manyata Tech Park Entrance (ORR)",
        "tdr1u9": "Jayanagar 4th Block Market Road",
        "tdr4hb": "Kalyan Nagar 80ft Road",
        "tdr4me": "Sahakar Nagar Main Road"
    }

    for _, row in parking_filtered.iterrows():
        bg_geo = row['geohash']
        violations = row['violation_count']

        # Get mapped Jakarta demand
        jk_geo = geo_mapping.get(bg_geo)
        baseline_demand = traffic_lookup.get(jk_geo, global_traffic_mean)

        # Calculate metrics
        metrics = calculate_traffic_impact(violations, baseline_demand)

        # Get name or general location name
        loc_name = dummy_names.get(bg_geo, f"Geohash {bg_geo} (Bengaluru)")

        hotspots.append({
            "geohash": bg_geo,
            "latitude": row['latitude'],
            "longitude": row['longitude'],
            "location_name": loc_name,
            "violations": int(violations),
            "baseline_demand": round(baseline_demand, 4),
            "remaining_capacity_pct": metrics["remaining_capacity_pct"],
            "cdi": metrics["cdi"],
            "delay_minutes": metrics["delay_minutes"],
            "tep": metrics["tep"],
            "economic_loss_rupees": metrics["economic_loss_rupees"]
        })

    # Sort by TEP (Targeted Enforcement Priority) descending to recommend highest-impact first
    hotspots = sorted(hotspots, key=lambda x: x['tep'], reverse=True)
    
    # Cap to top 80 hotspots to keep frontend rendering fast
    return jsonify(hotspots[:80])

@app.route('/api/hotspots/trend', methods=['GET'])
def get_hotspot_trend():
    geohash = request.args.get('geohash')
    day_of_week = int(request.args.get('day_of_week', 0))

    # Get hourly violation distribution for this geohash and day of week
    trend_data = df_parking[(df_parking['geohash'] == geohash) & (df_parking['day_of_week'] == day_of_week)]

    # Map to all 24 hours
    hourly_counts = {h: 0 for h in range(24)}
    for _, row in trend_data.iterrows():
        hourly_counts[int(row['hour'])] = int(row['violation_count'])

    counts_list = [hourly_counts[h] for h in range(24)]

    # Get mapped traffic demand trend
    jk_geo = geo_mapping.get(geohash)
    traffic_subset = df_traffic[(df_traffic['geohash'] == jk_geo) & (df_traffic['day_of_week'] == day_of_week)]
    
    hourly_demand = {h: 0.0 for h in range(24)}
    for _, row in traffic_subset.iterrows():
        hourly_demand[int(row['hour'])] = float(row['demand'])
        
    demand_list = [round(hourly_demand[h], 4) for h in range(24)]

    return jsonify({
        "violations": counts_list,
        "traffic_demand": demand_list
    })

@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.get_json()
    geohash = data.get('geohash')
    hour = int(data.get('hour', 9))
    day_of_week = int(data.get('day_of_week', 0))
    adjusted_violations = int(data.get('adjusted_violations', 0))

    # Look up baseline demand
    jk_geo = geo_mapping.get(geohash)
    traffic_subset = df_traffic[(df_traffic['hour'] == hour) & (df_traffic['day_of_week'] == day_of_week)]
    traffic_lookup = dict(zip(traffic_subset['geohash'], traffic_subset['demand']))
    global_traffic_mean = df_traffic[df_traffic['hour'] == hour]['demand'].mean() if len(df_traffic[df_traffic['hour'] == hour]) > 0 else 0.1
    baseline_demand = traffic_lookup.get(jk_geo, global_traffic_mean)

    # Re-calculate with adjusted count
    metrics = calculate_traffic_impact(adjusted_violations, baseline_demand)

    return jsonify({
        "geohash": geohash,
        "adjusted_violations": adjusted_violations,
        "baseline_demand": round(baseline_demand, 4),
        "remaining_capacity_pct": metrics["remaining_capacity_pct"],
        "cdi": metrics["cdi"],
        "delay_minutes": metrics["delay_minutes"],
        "tep": metrics["tep"],
        "economic_loss_rupees": metrics["economic_loss_rupees"]
    })

if __name__ == '__main__':
    print("Starting Flask Server...")
    app.run(debug=True, port=5000)
