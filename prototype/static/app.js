// Global variables
let map;
let markerGroup;
let hourlyChart;      // Per-location chart (floating panel)
let mainCityChart;    // City-wide chart (always visible below map)
let activeHotspot = null;
let currentHour = 9;
let currentDay = 0;

// Initialize Leaflet Map
function initMap() {
    // Center on Bengaluru City Center
    map = L.map('map', {
        zoomControl: true,
        scrollWheelZoom: true,
        attributionControl: false
    }).setView([12.9716, 77.5946], 12);

    // Standard light gray minimalist tile layer (perfect for light theme dashboard)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    markerGroup = L.layerGroup().addTo(map);

    // Prevent Leaflet from intercepting clicks on our custom UI controls
    const expandBtn = document.getElementById('expandMapBtn');
    if (expandBtn) {
        L.DomEvent.disableClickPropagation(expandBtn);
        L.DomEvent.disableScrollPropagation(expandBtn);
    }
}

// Fetch Hotspots from API
async function fetchHotspots() {
    try {
        const res = await fetch(`/api/hotspots?hour=${currentHour}&day_of_week=${currentDay}`);
        const data = await res.json();
        
        // Update stats
        document.getElementById('statHotspots').innerText = data.length;
        
        // Compute total city-wide economic loss in ₹
        const totalLoss = data.reduce((acc, curr) => acc + curr.economic_loss_rupees, 0);
        document.getElementById('statLoss').innerText = '₹' + totalLoss.toLocaleString('en-IN');

        // Clear existing markers
        markerGroup.clearLayers();

        // Populate Dispatch List & Render Map Markers
        const dispatchList = document.getElementById('dispatchList');
        dispatchList.innerHTML = '';

        if (data.length === 0) {
            dispatchList.innerHTML = '<li class="loading-item">No active violations detected.</li>';
            return;
        }

        data.forEach((hotspot, index) => {
            const TEP = hotspot.tep;
            
            // Marker color coding based on TEP
            let color = '#22c55e'; // Green (low)
            let badgeClass = 'badge-medium';
            let priorityText = 'Medium Priority';
            let pulseClass = '';
            
            if (TEP > 2.5) {
                color = '#dc2626'; // Red (high)
                badgeClass = 'badge-high';
                priorityText = 'Critical Priority';
                pulseClass = 'pulse-marker-high';
            } else if (TEP > 1.0) {
                color = '#d97706'; // Amber (medium)
                badgeClass = 'badge-medium';
                priorityText = 'High Priority';
                pulseClass = 'pulse-marker-medium';
            }

            // 1. Add Circle Marker to Leaflet Map
            const marker = L.circleMarker([hotspot.latitude, hotspot.longitude], {
                radius: Math.max(6, Math.min(18, hotspot.violations * 2)),
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.75,
                className: pulseClass
            });

            // Set Popup Content
            marker.bindPopup(`
                <div style="font-family: 'Inter', sans-serif;">
                    <strong style="font-size: 13px;">${hotspot.location_name}</strong><br>
                    <span style="font-size: 11px; color:#475569;">Geohash: ${hotspot.geohash}</span><br>
                    <hr style="margin: 6px 0; border: 0; border-top: 1px solid #e2e8f0;">
                    <span style="font-size: 11px;">Illegal Parked Cars: <strong>${hotspot.violations}</strong></span><br>
                    <span style="font-size: 11px;">Congestion Drag (CDI): <strong>${hotspot.cdi}</strong></span><br>
                    <span style="font-size: 11px; color: #dc2626;">Hourly Loss: <strong>₹${hotspot.economic_loss_rupees.toLocaleString('en-IN')}</strong></span>
                </div>
            `);

            marker.on('click', () => {
                inspectLocation(hotspot);
            });

            marker.addTo(markerGroup);

            // 2. Add to Sidebar High Priority Dispatch List (top 5 only)
            if (index < 5) {
                const li = document.createElement('li');
                li.className = 'dispatch-item';
                li.innerHTML = `
                    <div class="dispatch-info">
                        <span class="dispatch-loc">${hotspot.location_name}</span>
                        <span class="dispatch-count">${hotspot.violations} vehicles illegally parked</span>
                    </div>
                    <span class="dispatch-badge ${badgeClass}">${priorityText}</span>
                `;
                li.addEventListener('click', () => {
                    inspectLocation(hotspot);
                    map.setView([hotspot.latitude, hotspot.longitude], 14);
                    marker.openPopup();
                });
                dispatchList.appendChild(li);
            }
        });

        // Auto-update city-wide chart trends
        updateMainChart(data);

        // Keep current inspected hotspot synced if it is in the new list
        if (activeHotspot) {
            const updated = data.find(h => h.geohash === activeHotspot.geohash);
            if (updated) {
                inspectLocation(updated);
            }
        }

    } catch (err) {
        console.error("Error loading hotspots:", err);
    }
}

// Inspect Specific Hotspot
async function inspectLocation(hotspot) {
    activeHotspot = hotspot;
    
    // Slide open the panel
    const floatingPanel = document.getElementById('floatingPanel');
    if (floatingPanel) {
        floatingPanel.classList.add('open');
    }

    document.getElementById('inspectLocation').innerText = hotspot.location_name;
    document.getElementById('inspectGeohash').innerText = hotspot.geohash;
    document.getElementById('inspectViolations').innerText = hotspot.violations + ' vehicles';
    document.getElementById('inspectCapacity').innerText = hotspot.remaining_capacity_pct + '%';
    document.getElementById('inspectDelay').innerText = hotspot.delay_minutes + ' mins';

    // Set simulator slider max to the current violations count
    const slider = document.getElementById('simulateSlider');
    slider.max = hotspot.violations;
    slider.value = 0; // Default: 0 cleared cars
    document.getElementById('simulateCount').innerText = '0';
    document.getElementById('simulatedSaving').innerText = '₹0';

    // Fetch real historical trend for this geohash
    try {
        const res = await fetch(`/api/hotspots/trend?geohash=${hotspot.geohash}&day_of_week=${currentDay}`);
        const trendData = await res.json();
        if (hourlyChart) {
            // Update both violations and traffic demand datasets
            hourlyChart.data.datasets[0].data = trendData.violations;
            hourlyChart.data.datasets[0].label = `Parking Violations`;
            
            hourlyChart.data.datasets[1].data = trendData.traffic_demand;
            hourlyChart.data.datasets[1].label = `Traffic Demand`;
            
            hourlyChart.update();
        }
    } catch (err) {
        console.error("Error loading hotspot trend:", err);
    }
}

// Run What-If Simulation
async function runSimulation(clearedCount) {
    if (!activeHotspot) return;

    const adjustedCount = activeHotspot.violations - clearedCount;

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                geohash: activeHotspot.geohash,
                hour: currentHour,
                day_of_week: currentDay,
                adjusted_violations: adjustedCount
            })
        });
        const data = await res.json();

        // Update mini metrics dynamically
        document.getElementById('inspectCapacity').innerText = data.remaining_capacity_pct + '%';
        document.getElementById('inspectDelay').innerText = data.delay_minutes + ' mins';

        // Calculate Rupees ₹ Saved
        const originalLoss = activeHotspot.economic_loss_rupees;
        const newLoss = data.economic_loss_rupees;
        const savings = Math.max(0, originalLoss - newLoss);

        document.getElementById('simulatedSaving').innerText = '₹' + savings.toLocaleString('en-IN');

    } catch (err) {
        console.error("Simulation error:", err);
    }
}

// ============================================================
// CHART HELPERS
// ============================================================
function createDualLineChartConfig(gradientHeight) {
    return {
        labels: Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`),
        datasets: [
            {
                label: 'Parking Violations',
                data: Array(24).fill(0),
                borderColor: '#2563eb',
                borderWidth: 2.5,
                backgroundColor: null, // set per-canvas
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: '#2563eb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                yAxisID: 'y'
            },
            {
                label: 'Traffic Demand',
                data: Array(24).fill(0),
                borderColor: '#0f766e',
                borderWidth: 2,
                borderDash: [4, 4],
                backgroundColor: null,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: '#0f766e',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                yAxisID: 'y1'
            }
        ]
    };
}

function chartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    boxWidth: 12,
                    font: { size: 10, weight: '600', family: "'Inter', sans-serif" },
                    color: '#475569'
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#ffffff',
                bodyColor: '#e2e8f0',
                titleFont: { size: 11, weight: 'bold', family: "'Inter', sans-serif" },
                bodyFont: { size: 11, family: "'Inter', sans-serif" },
                padding: 10,
                cornerRadius: 8,
                borderColor: '#334155',
                borderWidth: 1
            }
        },
        scales: {
            y: {
                type: 'linear', display: true, position: 'left', beginAtZero: true,
                grid: { color: '#f1f5f9', drawBorder: false },
                ticks: { font: { size: 9, family: "'Inter', sans-serif" }, color: '#475569' },
                title: { display: true, text: 'Violating Vehicles', font: { size: 9, weight: '600', family: "'Inter', sans-serif" }, color: '#2563eb' }
            },
            y1: {
                type: 'linear', display: true, position: 'right', beginAtZero: true,
                grid: { drawOnChartArea: false, drawBorder: false },
                ticks: { font: { size: 9, family: "'Inter', sans-serif" }, color: '#475569' },
                title: { display: true, text: 'Congestion Demand', font: { size: 9, weight: '600', family: "'Inter', sans-serif" }, color: '#0f766e' }
            },
            x: {
                grid: { display: false, drawBorder: false },
                ticks: { font: { size: 8, family: "'Inter', sans-serif" }, color: '#94a3b8', maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }
            }
        }
    };
}

// ============================================================
// MAIN CITY-WIDE CHART (always visible below the map)
// ============================================================
function initMainChart() {
    const ctx = document.getElementById('mainChart').getContext('2d');

    const gViol = ctx.createLinearGradient(0, 0, 0, 190);
    gViol.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
    gViol.addColorStop(1, 'rgba(37, 99, 235, 0.0)');

    const gTraffic = ctx.createLinearGradient(0, 0, 0, 190);
    gTraffic.addColorStop(0, 'rgba(15, 118, 110, 0.15)');
    gTraffic.addColorStop(1, 'rgba(15, 118, 110, 0.0)');

    const data = createDualLineChartConfig(190);
    data.datasets[0].backgroundColor = gViol;
    data.datasets[1].backgroundColor = gTraffic;

    mainCityChart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: chartOptions()
    });
}

function updateMainChart(hotspots) {
    if (!mainCityChart) return;

    const baseCount = hotspots.reduce((acc, curr) => acc + curr.violations, 0);
    const hourlyDist = [
        0.05, 0.02, 0.01, 0.01, 0.02, 0.05,
        0.15, 0.25, 0.45, 0.65, 0.75, 0.85,
        0.90, 0.80, 0.75, 0.65, 0.70, 0.85,
        0.95, 0.90, 0.70, 0.45, 0.25, 0.10
    ];
    const trafficDist = [
        0.10, 0.08, 0.05, 0.05, 0.08, 0.15,
        0.45, 0.75, 0.85, 0.80, 0.70, 0.65,
        0.60, 0.62, 0.65, 0.70, 0.85, 0.95,
        0.80, 0.65, 0.45, 0.30, 0.20, 0.12
    ];

    mainCityChart.data.datasets[0].label = 'City-Wide Parking Violations';
    mainCityChart.data.datasets[0].data = hourlyDist.map(f => Math.round(baseCount * f * (0.85 + Math.random() * 0.3) / 10));

    mainCityChart.data.datasets[1].label = 'Avg Congestion Demand';
    mainCityChart.data.datasets[1].data = trafficDist.map(f => f * 0.95);

    mainCityChart.update();
}

// ============================================================
// LOCATION-SPECIFIC CHART (floating panel)
// ============================================================
function initPanelChart() {
    const ctx = document.getElementById('violationChart').getContext('2d');

    const gViol = ctx.createLinearGradient(0, 0, 0, 140);
    gViol.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
    gViol.addColorStop(1, 'rgba(37, 99, 235, 0.0)');

    const gTraffic = ctx.createLinearGradient(0, 0, 0, 140);
    gTraffic.addColorStop(0, 'rgba(15, 118, 110, 0.15)');
    gTraffic.addColorStop(1, 'rgba(15, 118, 110, 0.0)');

    const data = createDualLineChartConfig(140);
    data.datasets[0].backgroundColor = gViol;
    data.datasets[1].backgroundColor = gTraffic;

    hourlyChart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: chartOptions()
    });
}

// ============================================================
// EVENT LISTENERS
// ============================================================
function setupEvents() {
    const daySelect = document.getElementById('daySelect');
    const hourSlider = document.getElementById('hourSlider');
    const hourLabel = document.getElementById('hourLabel');
    const simulateSlider = document.getElementById('simulateSlider');
    const simulateCount = document.getElementById('simulateCount');
    const expandMapBtn = document.getElementById('expandMapBtn');
    const mapContainer = document.getElementById('mapContainer');
    const closePanelBtn = document.getElementById('closePanelBtn');
    const floatingPanel = document.getElementById('floatingPanel');

    daySelect.addEventListener('change', (e) => {
        currentDay = parseInt(e.target.value);
        fetchHotspots();
    });

    hourSlider.addEventListener('input', (e) => {
        currentHour = parseInt(e.target.value);
        hourLabel.innerText = `${currentHour.toString().padStart(2, '0')}:00`;
        fetchHotspots();
    });

    simulateSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        simulateCount.innerText = val;
        runSimulation(val);
    });

    // Map expand/minimize — in-place height toggle (not fullscreen)
    if (expandMapBtn) {
        L.DomEvent.disableClickPropagation(expandMapBtn);
        L.DomEvent.disableScrollPropagation(expandMapBtn);
        expandMapBtn.addEventListener('click', () => {
            const isExpanded = mapContainer.classList.toggle('map-expanded');
            if (isExpanded) {
                expandMapBtn.innerHTML = '<span class="btn-icon">⛶</span><span class="btn-text">Minimize Map</span>';
            } else {
                expandMapBtn.innerHTML = '<span class="btn-icon">⛶</span><span class="btn-text">Maximize Map</span>';
            }
            // Force Leaflet to adjust map tiles after the CSS height transition
            setTimeout(() => {
                map.invalidateSize();
            }, 380);
        });
    }

    // Floating panel close button
    if (closePanelBtn) {
        L.DomEvent.disableClickPropagation(closePanelBtn);
        closePanelBtn.addEventListener('click', () => {
            floatingPanel.classList.remove('open');
            activeHotspot = null;
        });
    }

    // Prevent map interactions inside the floating panel
    if (floatingPanel) {
        L.DomEvent.disableClickPropagation(floatingPanel);
        L.DomEvent.disableScrollPropagation(floatingPanel);
    }
}

// ============================================================
// INITIALIZE ON LOAD
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
    initMap();
    initMainChart();
    initPanelChart();
    setupEvents();
    fetchHotspots();
});
