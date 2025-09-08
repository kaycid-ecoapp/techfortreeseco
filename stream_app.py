# force rebuild

import streamlit as st
import requests
import time
from geopy.distance import geodesic

# --- Postcode lookup ---
def lookup_postcode(postcode):
    postcode = postcode.lower().strip()
    if not postcode:
        return [54.5, -1.5]
    try:
        api_url = f"https://api.postcodes.io/postcodes/{postcode}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200 and "result" in data:
                lat = data["result"]["latitude"]
                lon = data["result"]["longitude"]
                return [lat, lon]
    except:
        pass
    return [54.5, -1.5]

# --- Tree planting site logic ---
tree_sites = {
    "Northumberland": [55.2, -1.6],
    "Yorkshire": [53.9, -1.1],
    "London": [51.5, -0.1],
    "Manchester": [53.5, -2.2]
}

def get_tree_site(postcode):
    postcode = postcode.lower()
    if postcode.startswith("ne"):
        return tree_sites["Northumberland"]
    elif postcode.startswith("yo"):
        return tree_sites["Yorkshire"]
    elif postcode.startswith("n1") or postcode.startswith("e"):
        return tree_sites["London"]
    elif postcode.startswith("m"):
        return tree_sites["Manchester"]
    else:
        return [54.5, -1.5]

# --- Overpass API search with deduplication + nearest-first ---
def get_nearby_places_overpass(lat, lon, osm_filter):
    overpass_url = "https://overpass-api.de/api/interpreter"
    radius_m = 8046  # 5 miles in meters
    query = f"""
    [out:json];
    (
      node[{osm_filter}](around:{radius_m},{lat},{lon});
      way[{osm_filter}](around:{radius_m},{lat},{lon});
      relation[{osm_filter}](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    try:
        response = requests.post(overpass_url, data={"data": query}, timeout=25)
        response.raise_for_status()
        data = response.json()
        seen = set()
        places = []
        for element in data["elements"]:
            if "lat" in element:
                el_lat, el_lon = element["lat"], element["lon"]
            elif "center" in element:
                el_lat, el_lon = element["center"]["lat"], element["center"]["lon"]
            else:
                continue

            name = element.get("tags", {}).get("name", osm_filter)
            address_parts = [v for k, v in element.get("tags", {}).items()
                             if k in ["addr:street", "addr:postcode", "addr:city"]]
            address = ", ".join(address_parts) if address_parts else "No address"

            key = (name, round(el_lat, 5), round(el_lon, 5))
            if key in seen:
                continue
            seen.add(key)

            distance = round(geodesic((lat, lon), (el_lat, el_lon)).miles, 3)
            places.append({
                "name": name,
                "address": address,
                "lat": el_lat,
                "lon": el_lon,
                "distance": distance
            })

        # ✅ Sort and limit to 5 closest
        return sorted(places, key=lambda p: p["distance"])[:5]
    except Exception as e:
        st.error(f"Error fetching {osm_filter} data: {e}")
        return []

# --- Streamlit UI ---
st.set_page_config(page_title="Tech for Trees", page_icon="🌱", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(to bottom right, #b2d8b2, #e6f2e6);
        color: #333;
    }
    h1, h2, h3 {
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Tech for Trees 🌱")
st.subheader("Donate your old tech and pledge trees for planting across the UK.")

name = st.text_input("What's your name?")
if name:
    st.write(f"Welcome, {name}! 🌿 Let's get started.")

item_count = st.number_input("How many items are you donating?", min_value=1, step=1)
postcode = st.text_input("Enter your postcode (e.g. NE23)").lower().strip()

show_schools = st.checkbox("Show nearby schools", value=True)
show_supermarkets = st.checkbox("Show nearby supermarkets", value=True)
show_post_offices = st.checkbox("Show nearby post offices", value=True)
show_recycling = st.checkbox("Show nearby recycling centres", value=True)

if st.button("Donate"):
    st.success(f"Thanks {name if name else 'friend'}! You've pledged {item_count} item(s) from {postcode.upper()}.")
    time.sleep(0.5)
    lat, lon = lookup_postcode(postcode)

    all_places = []

    if show_schools:
        for place in get_nearby_places_overpass(lat, lon, 'amenity=school'):
            all_places.append({"type": "🏫 School", **place})

    if show_supermarkets:
        for place in get_nearby_places_overpass(lat, lon, 'shop=supermarket'):
            all_places.append({"type": "🛒 Supermarket", **place})

    if show_post_offices:
        for place in get_nearby_places_overpass(lat, lon, 'amenity=post_office'):
            all_places.append({"type": "📮 Post Office", **place})

    if show_recycling:
        for place in get_nearby_places_overpass(lat, lon, 'amenity=recycling'):
            all_places.append({"type": "♻️ Recycling Centre", **place})

    st.markdown("---")
    st.subheader("📍 Your Drop-off Locations")
    st.info(f"📍 Your location: {postcode.upper()}")

    if all_places:
        all_places = sorted(all_places, key=lambda p: p["distance"])[:5]
        for i, place in enumerate(all_places, 1):
            st.write(f"**{i}. {place['type']}**: {place['name']}")
            st.write(f"📍 {place['address']} — {place['distance']} miles away")
            st.write("")
    else:
        st.write("**No specific drop-off locations found nearby.**")

    tree_coords = get_tree_site(postcode)
    region = "your region"
    if postcode.startswith("ne"):
        region = "Northumberland"
    elif postcode.startswith("yo"):
        region = "Yorkshire"
    elif postcode.startswith("n") or postcode.startswith("e"):
        region = "London area"
    elif postcode.startswith("m"):
        region = "Manchester area"

    st.markdown("---")
    st.subheader("🌲 Tree Planting Location")
    st.success(f"🌳 Your {item_count} tree(s) will be planted in {region}!")
    st.write(f"**Region:** {region}")
    st.write("Your contribution helps create green spaces and fight climate change! 🌍")
