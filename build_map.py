#!/usr/bin/env python3
"""Rebuild foster_map_final.html from animals.csv.

Same map as UDR_foster_map.ipynb (final assembly), with two changes:
  * geocoding results are cached in geocode_cache.json (so only NEW cities are looked up)
  * the "Time in Foster" legend starts expanded
Run:  pip install pandas folium geopy   then   python build_map.py
"""
import json
import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster

CSV_PATH = "animals.csv"
OUT_PATH = "foster_map_final.html"
CACHE_PATH = "geocode_cache.json"

df = pd.read_csv(CSV_PATH)

df_fostered = df[
    df["City"].notna() & (df["City"] != "") &
    df["State"].notna() & (df["State"] != "")
].reset_index(drop=True)

df_needs_foster = df[
    ((df["City"].isna()) | (df["City"] == "")) &
    ((df["State"].isna()) | (df["State"] == ""))
].reset_index(drop=True)

# ---- Geocoding with a cache ----
try:
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)
except (FileNotFoundError, ValueError):
    cache = {}

_geocode = None
def get_coordinates(city, state):
    global _geocode
    key = f"{city}, {state}"
    if key in cache:
        return tuple(cache[key])
    try:
        if _geocode is None:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
            geolocator = Nominatim(user_agent="udr-foster-map (github.com/UnitedDobermanRescue/UDR)")
            _geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)
        location = _geocode(key)
        if location:
            cache[key] = [location.latitude, location.longitude]
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Error geocoding {key}: {type(e).__name__}")
    return None, None

coords = df_fostered.apply(lambda r: get_coordinates(r["City"], r["State"]),
                           axis=1, result_type="expand")
df_fostered[["lat", "lon"]] = coords
missing = df_fostered[df_fostered["lat"].isna()]
for _, r in missing.iterrows():
    print(f"WARNING: could not place {r['Name']} ({r['City']}, {r['State']}); skipped")
df_fostered = df_fostered.dropna(subset=["lat", "lon"]).reset_index(drop=True)
with open(CACHE_PATH, "w", encoding="utf-8") as f:
    json.dump(cache, f, indent=1, sort_keys=True)

base_url = "https://www.uniteddobermanrescue.org"
rescue_groups_url = "https://rescuegroups.org/manage/animals#datatable74={%22limit%22:25,%22page%22:1,%22start%22:0,%22sortbyFieldID%22:1499,%22sortorder%22:%22asc%22,%22viewID%22:%22112%22,%22viewType%22:%22Built-in%22,%22togglethumbnails%22:%22Off%22,%22searchEnabled%22:false}&"
intakes_url = "https://rescuegroups.org/manage/animals_intakes#datatable387={%22limit%22:%2225%22,%22page%22:1,%22start%22:0,%22sortbyFieldID%22:%22%22,%22sortorder%22:%22asc%22,%22viewID%22:%22211%22,%22viewType%22:%22Built-in%22,%22searchEnabled%22:false}&"


search_html = """
<style>
#search-container { position: fixed; top: 70px; left: 10px; z-index: 999997; width: 240px; }
#dog-search { width: 100%; padding: 8px 12px; border: 2px solid #2c3e50; border-radius: 20px; outline: none; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }
</style>
<div id="search-container"><input type="text" id="dog-search" placeholder="Search dogs by name..." oninput="filterDogs()"></div>
"""


sidebar_html = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<style>
#sidebar {
    position: fixed;
    top: 0;
    right: -420px;
    width: 420px;
    height: 100%;
    background: white;
    border-left: 3px solid #444;
    overflow-y: auto;
    transition: right 0.3s ease;
    z-index: 999999;
    font-family: Arial, sans-serif;
}
#sidebar.open { right: 0; }
#sidebar-close {
    cursor: pointer;
    font-size: 28px;
    font-weight: bold;
    float: right;
    margin: 15px;
    padding: 10px 20px;
}
.tab-container { margin-top: 65px; }
.tab-buttons { display: flex; border-bottom: 2px solid #ccc; }
.tab-buttons button {
    flex: 1; padding: 18px; background: #eee;
    border: none; cursor: pointer; font-weight: bold;
    font-size: 16px;
}
.tab-buttons button.active {
    background: #ddd; border-bottom: 3px solid #444;
}
.tab-content { display: none; padding: 15px; }
.tab-content.active { display: block; }
#sidebar img { width: 100%; border-radius: 6px; margin-bottom: 10px; }

#page-header {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: rgba(255, 255, 255, 0.95);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px 0;
    font-family: Arial, sans-serif;
    z-index: 9999;
    border-bottom: 2px solid #444;
}
#page-header img {
    height: 35px;
    margin-right: 10px;
}
#header-title {
    font-size: 20px;
    font-weight: bold;
}

/* Mobile Specific Overrides */
@media only screen and (max-width: 600px) {
    #sidebar {
        width: 90% !important;
        right: -90%;
    }
    #header-title {
        font-size: 16px;
    }
    #search-container, #needs-foster-panel {
        width: 180px !important;
    }
    .foster-item {
        padding: 15px !important; /* Larger touch target */
    }
}
</style>

<div id="page-header">
    <img src="https://s3.amazonaws.com/imagesroot.rescuegroups.org/webpages/s8319n8fohztfmoo.jpg" alt="UDR Logo">
    <div id="header-title">UDR Foster Map</div>
</div>

<div id="sidebar">
    <span id="sidebar-close">✕</span>

    <div class="tab-container">
        <div class="tab-buttons">
            <button class="tab-btn active" onclick="openTab('details')">Details</button>
            <button class="tab-btn" onclick="openTab('links')">Links</button>
        </div>

        <div id="details" class="tab-content active">
            <div id="photos"></div>
            <div id="videos"></div>
            <div id="info-text"></div>
        </div>
        <div id="links" class="tab-content"></div>
    </div>
</div>

<script>
document.getElementById("sidebar-close").onclick = function() {
    document.getElementById("sidebar").classList.remove("open");
};

function openSidebar() {
    document.getElementById("sidebar").classList.add("open");
}

function openTab(tabName) {
    var tabs = document.getElementsByClassName("tab-content");
    var buttons = document.getElementsByClassName("tab-btn");

    for (var i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove("active");
        buttons[i].classList.remove("active");
    }

    document.getElementById(tabName).classList.add("active");
    if(tabName === 'details') buttons[0].classList.add("active");
    else buttons[1].classList.add("active");
}
</script>
"""


needs_foster_html = """
<style>
#needs-foster-panel {
    position: fixed;
    top: 115px; /* Moved down to accommodate header and search bar */
    left: 10px;
    z-index: 999998;
    background: white;
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 0;
    max-height: 50%;
    width: 240px;
    overflow: hidden;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
#needs-foster-header {
    background: #2c3e50;
    color: white;
    padding: 10px 15px;
    margin: 0;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #ddd;
}
#needs-foster-header:hover {
    background: #34495e;
}
#foster-list {
    display: none;
    list-style-type: none;
    padding: 0;
    margin: 0;
    max-height: 300px;
    overflow-y: auto;
}
.foster-item {
    padding: 8px 15px;
    border-bottom: 1px solid #f1f1f1;
    transition: all 0.2s ease;
    font-size: 13px;
    font-weight: 400;
    color: #444;
    cursor: pointer;
}
.foster-item:hover {
    background: #f8f9fa;
    color: #c0392b;
    padding-left: 18px;
}
</style>

<div id="needs-foster-panel">
    <h3 id="needs-foster-header" onclick="toggleFosterList()">
        Dogs Needing Foster <span style='font-size: 9px;'>▼</span>
    </h3>
    <ul id="foster-list">
"""

for list_index, row in df_needs_foster.iterrows():
    needs_foster_html += f"<li class='foster-item' onclick='window.openDogFromList({list_index})'>{row['Name']}</li>"

needs_foster_html += """
    </ul>
</div>
"""


def foster_color(days):
    if pd.isna(days):
        return "lightred"
    if days < 30:
        return "lightred"
    if days < 90:
        return "red"
    if days < 180:
        return "darkred"
    return "black"


bottom_links = """
<div style="
    position: fixed;
    bottom: 10px;
    left: 10px;
    background: white;
    padding: 8px;
    border: 1px solid grey;
    font-family: Arial, sans-serif;
    z-index: 99999;
    text-align: left;
    font-size: 11px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
">
    <a href=\"https://www.uniteddobermanrescue.org/animals/browse\" target=\"_blank\">
        Browse All Dogs
    </a><br>

    <a href=\"https://tinyurl.com/msffpcsa\" target=\"_blank\">
        Database Report
    </a>
</div>
"""


legend_html = """
<style>
#map-legend {
    position: fixed;
    bottom: 35px;
    right: 20px;
    z-index: 999998;
    background: white;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    width: 190px;
    overflow: hidden;
}
#legend-header {
    background: #b2bec3; /* Darker coordinating grey */
    color: #2d3436;
    padding: 10px;
    border-bottom: 2px solid #636e72;
    cursor: pointer;
    font-weight: 600;
    text-align: center;
    font-size: 14px;
}
#legend-header:hover {
    background: #9fa8a3;
}
#legend-content {
    display: block;
    padding: 12px;
}
.legend-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    font-size: 12px;
    font-weight: 500;
}
.legend-color {
    width: 20px;
    height: 20px;
    margin-right: 12px;
    border-radius: 50%;
    border: 1px solid rgba(0,0,0,0.2);
}
</style>

<div id="map-legend">
    <div id="legend-header" onclick="toggleLegend()">Time in Foster ⓘ</div>
    <div id="legend-content">
        <div class="legend-item"><div class="legend-color" style="background: #ffcdd2; border: 2px solid #ef5350;"></div> < 30 Days</div>
        <div class="legend-item"><div class="legend-color" style="background: #ef5350;"></div> 30 - 89 Days</div>
        <div class="legend-item"><div class="legend-color" style="background: #b71c1c;"></div> 90 - 179 Days</div>
        <div class="legend-item"><div class="legend-color" style="background: #000000;"></div> 180+ Days</div>
    </div>
</div>

<script>
function toggleLegend() {
    var content = document.getElementById('legend-content');
    content.style.display = (window.getComputedStyle(content).display === 'none') ? 'block' : 'none';
}
</script>
"""


import json

# Prepare Data for Dogs Needing Foster
needs_foster_data = []
for idx, row in df_needs_foster.iterrows():
    d_html = f"<h2>{row['Name']}</h2><b>Status:</b> {row.get('Status', 'N/A')}<br><b>Sex:</b> {row.get('Sex', 'N/A')}<br><b>Description:</b><br>{row.get('Description', 'No description available.')}"
    p_html = ""
    for p in ["Picture 1", "Picture 2", "Picture 3", "Picture 4"]:
        if pd.notna(row.get(p)) and str(row[p]).strip() != "":
            full_img_url = base_url + str(row[p]) if str(row[p]).startswith('/') else str(row[p])
            p_html += f"<img src='{full_img_url}' style='width:100%; margin-bottom:10px; border-radius:5px;' />"
    l_html = (
        f"<a href='https://www.uniteddobermanrescue.org/animals/detail?AnimalID={row.get('Animal ID', '')}' target='_blank'>Foster Dog's Full Profile</a><br><br>"
        f"<a href='{rescue_groups_url}' target='_blank'>Rescue Groups - Available Dogs List</a><br><br>"
        f"<a href='{intakes_url}' target='_blank'>Rescue Groups - Intake</a>"
    )
    needs_foster_data.append({"details": d_html, "photos": p_html, "videos": "", "links": l_html})


sidebar_js_template = """
<script>
    window.markerData = DATA_FOSTERED;
    window.needsData = DATA_NEEDS;

    function toggleFosterList() {
        var el = document.getElementById('foster-list');
        if (el) el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'block' : 'none';
    }

    window.openDogFromList = function(index) {
        if (window.needsData && window.needsData[index]) {
            window.updateSidebar(window.needsData[index]);
        }
    };

    window.updateSidebar = function(data) {
        if (!data) return;
        document.getElementById('photos').innerHTML = data.photos || '';
        document.getElementById('videos').innerHTML = data.videos || '';
        document.getElementById('info-text').innerHTML = data.details || '';
        document.getElementById('links').innerHTML = data.links || '';
        document.getElementById('sidebar').classList.add('open');

        var tabs = document.getElementsByClassName("tab-content");
        var buttons = document.getElementsByClassName("tab-btn");
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].classList.remove("active");
            buttons[i].classList.remove("active");
        }
        document.getElementById('details').classList.add('active');
        buttons[0].classList.add("active");
    };
</script>
"""


filter_js = """
<script>
    function filterDogs() {
        var searchTerm = document.getElementById('dog-search').value.toLowerCase();
        var map = null;
        var markerCluster = null;

        // Find the map and cluster objects globally
        for (var key in window) {
            if (window[key] instanceof L.Map) {
                map = window[key];
            }
            if (window[key] instanceof L.MarkerClusterGroup) {
                markerCluster = window[key];
            }
        }

        if (!map || !markerCluster) {
            console.warn("Map or MarkerCluster not found for filtering.");
            return;
        }

        // Clear existing markers from the cluster
        markerCluster.clearLayers();

        window.markerData.forEach(function(dog) {
            // The 'name' property is now available in `window.markerData`
            // Also lat, lon, iconColor are available.
            if (dog.name.toLowerCase().includes(searchTerm)) {
                // Recreate marker and add to cluster
                var marker = L.marker([dog.lat, dog.lon], {
                    icon: L.AwesomeMarkers.icon({
                        icon: 'paw',
                        prefix: 'fa',
                        markerColor: dog.iconColor // Use the stored color
                    }),
                    // Set tooltip (name) and animalId for event binding
                    title: dog.name,
                    animalId: dog.id
                });
                markerCluster.addLayer(marker);

                // Re-bind click event for the newly created marker
                marker.on('click', function(e) {
                    var dogId = e.target.options.animalId;
                    var data = window.markerData.find(d => String(d.id) === String(dogId));
                    if (data) window.updateSidebar(data);
                });
            }
        });

        // Note: Filtering for 'needs-foster' dogs is not part of this search bar's current scope.
    }
</script>
"""


js_needs = json.dumps(needs_foster_data)

# 1. Re-initialize Map and Cluster
m = folium.Map(location=[39.5, -98.35], zoom_start=5)
cluster = MarkerCluster().add_to(m)

# 2. Build Data and Markers using Animal ID as a primary key
final_fostered_list = []

for i, (idx, row) in enumerate(df_fostered.iterrows()):
    animal_id = str(row['Animal ID'])
    dog_name = row['Name'] # Get the dog's name
    dog_lat = row['lat'] # Get latitude
    dog_lon = row['lon'] # Get longitude
    dog_icon_color = foster_color(row['Days in Foster']) # Get calculated color

    details_html = (f"<h2>{dog_name}</h2><b>Status:</b> {row['Status']}<br><b>Sex:</b> {row['Sex']}<br>"
                    f"<b>Age:</b> {row['General Age']} <br><b>Energy:</b> {row['Energy Level']}<br>"
                    f"<b>City:</b> {row['City']}<br><b>State:</b> {row['State']}<br>"
                    f"<b>Days in Foster:</b> {row['Days in Foster']}<br><br><b>Description:</b><br>{row['Description']}")

    # Photos removed per user request
    photos_html = ""

    # Updated Link Labels and URLs per request
    links_html = (f"<a href='https://www.uniteddobermanrescue.org/animals/detail?AnimalID={animal_id}' target='_blank'>Public Website - Full Profile</a><br><br>"
                  f"<a href='https://rescuegroups.org/manage/animals#datatable74={{%22limit%22:25,%22page%22:1,%22start%22:0,%22sortbyFieldID%22:1499,%22sortorder%22:%22asc%22,%22viewID%22:%22112%22:%22viewType%22:%22Built-in%22,%22togglethumbnails%22:%22Off%22,%22searchEnabled%22:false}}&' target='_blank'>RescueGroups - Available Dogs Report</a><br><br>"
                  f"<a href='https://rescuegroups.org/manage/animals_intakes#datatable387={{%22limit%22:%2225%22:%22page%22:1,%22start%22:0,%22sortbyFieldID%22:%22%22,%22sortorder%22:%22asc%22,%22viewID%22:%22211%22:%22viewType%22:%22Built-in%22:%22searchEnabled%22:false}}&' target='_blank'>RescueGroups - Intake Report</a>")

    final_fostered_list.append({
        "id": animal_id,
        "lat": dog_lat,
        "lon": dog_lon,
        "name": dog_name,
        "iconColor": dog_icon_color,
        "details": details_html,
        "photos": photos_html,
        "videos": "",
        "links": links_html
    })

    marker = folium.Marker(
        location=[dog_lat, dog_lon],
        icon=folium.Icon(color=dog_icon_color),
        tooltip=dog_name
    )
    marker.add_to(cluster)
    marker.options['animalId'] = animal_id

# 3. Enhanced JS Sync Engine (Auto-detects Map and Cluster)
final_js = sidebar_js_template.replace("DATA_FOSTERED", json.dumps(final_fostered_list)).replace("DATA_NEEDS", js_needs)


primary_key_sync_js = """
<script>
function applyPrimaryKeySync() {
    console.log("Searching for Map and Cluster objects...");

    var foundMap = null;
    var foundCluster = null;

    // Search global scope for Leaflet objects
    for (var key in window) {
        if (window[key] instanceof L.Map) {
            foundMap = window[key];
        }
        if (window[key] instanceof L.MarkerClusterGroup) {
            foundCluster = window[key];
        }
    }

    if (foundMap && foundCluster && foundCluster._featureGroup) {
        console.log("Map and Cluster found. Binding clicks...");
        foundCluster.eachLayer(function(marker) {
            if (marker instanceof L.Marker && marker.options.animalId) {
                marker.off('click');
                marker.on('click', function(e) {
                    var dogId = e.target.options.animalId;
                    var data = window.markerData.find(d => String(d.id) === String(dogId));
                    if (data) window.updateSidebar(data);
                });
            }
        });
        console.log("Sync engine active.");
    } else {
        console.log("Still waiting for Leaflet objects... retrying");
        setTimeout(applyPrimaryKeySync, 1000);
    }
}
setTimeout(applyPrimaryKeySync, 1500);
</script>
"""


# 4. Final Assembly
m.get_root().html._children = {}
m.get_root().html.add_child(folium.Element(sidebar_html))
m.get_root().html.add_child(folium.Element(needs_foster_html))
m.get_root().html.add_child(folium.Element(legend_html))
m.get_root().html.add_child(folium.Element(bottom_links))
m.get_root().html.add_child(folium.Element(search_html))
m.get_root().html.add_child(folium.Element(filter_js))
m.get_root().html.add_child(folium.Element('{% raw %}' + final_js + '{% endraw %}'))
m.get_root().html.add_child(folium.Element(primary_key_sync_js))

m.save(OUT_PATH)
print(f"Saved {OUT_PATH}: {len(final_fostered_list)} dogs on map, {len(df_needs_foster)} needing foster")
