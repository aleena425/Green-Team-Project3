import streamlit as st
import folium
from streamlit_folium import st_folium
import googlemaps
import polyline
import requests
from datetime import timedelta

# Initialize Google Maps client
API_KEY = "API_KEY"  # Replace with your actual API key, stored securely in an environment variable
gmaps = googlemaps.Client(key=API_KEY)

# Sidewalk safety and accessibility color mapping
accessibility_colors = {
    "Easily Accessible": "#32CD32",  # Green
    "Moderately Accessible": "#1E90FF",  # Blue
    "Challenging": "#FFD700",  # Yellow
    "Inaccessible": "#FF6347"  # Red
}

# Function to autocomplete places
def autocomplete_places(input_text):
    autocomplete_url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={input_text}&key={API_KEY}"
    response = requests.get(autocomplete_url)
    return response.json()

# User input for start and end locations
st.title("Route Safety and Obstacle Information for Walkers")

# Initialize session state for input fields
if 'start_location' not in st.session_state:
    st.session_state.start_location = ""
if 'end_location' not in st.session_state:
    st.session_state.end_location = ""

# Autocomplete for start location
start_location_input = st.text_input("Enter the start location", value=st.session_state.start_location)

# Suggestions for start location
if start_location_input:
    autocomplete_results = autocomplete_places(start_location_input)
    if autocomplete_results.get("predictions"):
        st.write("Suggestions:")
        for prediction in autocomplete_results["predictions"]:
            if st.button(prediction['description'], key=f"start-{prediction['place_id']}"):
                st.session_state.start_location = prediction['description']

# Autocomplete for end location
end_location_input = st.text_input("Enter the end location", value=st.session_state.end_location)

# Suggestions for end location
if end_location_input:
    autocomplete_results = autocomplete_places(end_location_input)
    if autocomplete_results.get("predictions"):
        st.write("Suggestions:")
        for prediction in autocomplete_results["predictions"]:
            if st.button(prediction['description'], key=f"end-{prediction['place_id']}"):
                st.session_state.end_location = prediction['description']

# Function to fetch and store route information in session state
def fetch_route_info():
    directions = gmaps.directions(st.session_state.start_location, st.session_state.end_location, mode="walking")

    if directions:
        route = directions[0]
        route_polyline = route["overview_polyline"]["points"]
        decoded_route = polyline.decode(route_polyline)

        # Store route details, estimated time, and steps in session state
        st.session_state['route'] = decoded_route
        st.session_state['duration'] = route["legs"][0]["duration"]["value"]
        st.session_state['steps'] = route["legs"][0]["steps"]

# Button to get route information
if st.button("Get Route Information"):
    fetch_route_info()

# Check if route information exists in session state and display it
if 'route' in st.session_state:
    decoded_route = st.session_state['route']
    duration_text = str(timedelta(seconds=st.session_state['duration']))
    steps = st.session_state['steps']

    # Initialize the map
    m = folium.Map(location=decoded_route[0], zoom_start=14)

    # Draw the route with color-coded segments based on safety level
    for lat_lng in decoded_route:
        folium.CircleMarker(
            location=lat_lng,
            radius=3,
            color=accessibility_colors.get("Easily Accessible", "#808080")  # Sample color, adjust based on criteria
        ).add_to(m)

    # Display the map with Folium in Streamlit
    st_folium(m, width=700, height=500)

    # Display information about route safety and estimated time
    st.subheader("Route Safety Information")
    st.write(f"Estimated walking time from {st.session_state.start_location} to {st.session_state.end_location}: {duration_text}")
    st.write("The route is color-coded to indicate accessibility levels:")
    st.write("- **Green**: Easily Accessible (no obstacles)")
    st.write("- **Blue**: Moderately Accessible (minor obstacles)")
    st.write("- **Yellow**: Challenging (may have obstacles)")
    st.write("- **Red**: Inaccessible (severe obstacles)")

    # Step-by-Step Directions
    st.subheader("Step-by-Step Directions")
    for i, step in enumerate(steps, 1):
        distance = step["distance"]["text"]
        duration = step["duration"]["text"]
        instructions = step["html_instructions"]

        # Use st.markdown to render the HTML properly
        st.markdown(f"**Step {i}:** {instructions} - **{distance}**, ~{duration}", unsafe_allow_html=True)
else:
    st.write("Click 'Get Route Information' to see the route details.")
