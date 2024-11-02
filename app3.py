import streamlit as st
import folium
from streamlit_folium import st_folium
import googlemaps
import polyline
import requests
from datetime import timedelta
import random  # For generating synthetic accessibility data
import pandas as pd
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing.image import img_to_array
import os

# Initialize Google Maps client
API_KEY = "API_KEY_HERE"  # Replace with your actual API key
gmaps = googlemaps.Client(key=API_KEY)

# Sidewalk safety and accessibility color mapping
accessibility_colors = {
    "Easily Accessible": "#32CD32",  # Green
    "Moderately Accessible": "#1E90FF",  # Blue
    "Challenging": "#FFD700",  # Yellow
    "Inaccessible": "#FF6347"  # Red
}

# Dataset path for storing reports
dataset_path = "sidewalk_hazards.csv"

# Load or create the hazards dataset
try:
    data = pd.read_csv(dataset_path)
except FileNotFoundError:
    data = pd.DataFrame(columns=["Hazard_ID", "Description", "Severity_Level", "Accessibility", "Address", "Latitude", "Longitude", "Image_Path"])

# Function to autocomplete places
def autocomplete_places(input_text):
    autocomplete_url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={input_text}&key={API_KEY}"
    try:
        response = requests.get(autocomplete_url)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching autocomplete results: {e}")
        return {"predictions": []}

# Function to fetch and store route information in session state
def fetch_route_info():
    try:
        directions = gmaps.directions(st.session_state.start_location, st.session_state.end_location, mode="walking")
        if directions:
            route = directions[0]
            route_polyline = route["overview_polyline"]["points"]
            decoded_route = polyline.decode(route_polyline)
            
            # Generate synthetic accessibility data for each point on the route
            synthetic_route = []
            for point in decoded_route:
                accessibility_level = random.choice(list(accessibility_colors.keys()))
                synthetic_route.append((point, accessibility_level))
            
            # Store route details, estimated time, and steps in session state
            st.session_state['route'] = synthetic_route
            st.session_state['duration'] = route["legs"][0]["duration"]["value"]
            st.session_state['steps'] = route["legs"][0]["steps"]
        else:
            st.error("No route found. Please check the start and end locations.")
    except googlemaps.exceptions.ApiError as e:
        st.error(f"Google Maps API Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# Title and inputs for start and end locations
st.title("Route Safety and Obstacle Information for Walkers")

if 'start_location' not in st.session_state:
    st.session_state.start_location = ""
if 'end_location' not in st.session_state:
    st.session_state.end_location = ""

# Autocomplete for start location
start_location_input = st.text_input("Enter the start location", value=st.session_state.start_location)
if start_location_input:
    autocomplete_results = autocomplete_places(start_location_input)
    if autocomplete_results.get("predictions"):
        st.write("Suggestions:")
        for prediction in autocomplete_results["predictions"]:
            if st.button(prediction['description'], key=f"start-{prediction['place_id']}"):
                st.session_state.start_location = prediction['description']

# Autocomplete for end location
end_location_input = st.text_input("Enter the end location", value=st.session_state.end_location)
if end_location_input:
    autocomplete_results = autocomplete_places(end_location_input)
    if autocomplete_results.get("predictions"):
        st.write("Suggestions:")
        for prediction in autocomplete_results["predictions"]:
            if st.button(prediction['description'], key=f"end-{prediction['place_id']}"):
                st.session_state.end_location = prediction['description']

# Button to get route information
if st.button("Get Route Information"):
    fetch_route_info()

# Display route on map and step-by-step directions
if 'route' in st.session_state:
    route_data = st.session_state['route']
    duration_text = str(timedelta(seconds=st.session_state['duration']))
    steps = st.session_state['steps']

    # Initialize map
    m = folium.Map(location=route_data[0][0], zoom_start=14)

    for lat_lng, accessibility_level in route_data:
        folium.CircleMarker(
            location=lat_lng,
            radius=3,
            color=accessibility_colors[accessibility_level],
            fill=True
        ).add_to(m)

    st_folium(m, width=700, height=500)

    st.subheader("Route Safety Information")
    st.write(f"Estimated walking time: {duration_text}")
    st.write("Accessibility levels: Green (Easily Accessible), Blue (Moderately Accessible), Yellow (Challenging), Red (Inaccessible)")

    # Step-by-Step Directions
    st.subheader("Step-by-Step Directions")
    for i, step in enumerate(steps, 1):
        distance = step["distance"]["text"]
        duration = step["duration"]["text"]
        instructions = step["html_instructions"]
        st.markdown(f"**Step {i}:** {instructions} - **{distance}**, ~{duration}", unsafe_allow_html=True)

# Hazard Reporting
st.subheader("Report a Sidewalk Hazard")
with st.form("report_form"):
    description = st.text_input("Describe the hazard")
    severity = st.selectbox("Select severity level", ["Low", "Moderate", "High", "Severe"])
    accessibility = st.selectbox("Accessibility Level", list(accessibility_colors.keys()))
    location = st.text_input("Location (address or coordinates)")
    uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    submitted = st.form_submit_button("Submit Report")

    if submitted:
        # Define the directory to save uploaded images
        image_dir = "uploaded_images"
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        # Save image if uploaded
        image_path = None
        if uploaded_image:
            image = Image.open(uploaded_image).convert("RGB")
            image_path = os.path.join(image_dir, uploaded_image.name)
            image.save(image_path)

            # Image recognition
            model = MobileNetV2(weights="imagenet")
            img_array = img_to_array(image.resize((224, 224)))
            img_array = preprocess_input(img_array.reshape((1, 224, 224, 3)))
            predictions = model.predict(img_array)
            results = decode_predictions(predictions, top=3)[0]
            st.write("Predictions:")
            for _, label, prob in results:
                st.write(f"{label}: {prob * 100:.2f}%")

        # Append new report to dataset
        new_report = pd.DataFrame({
            "Hazard_ID": [len(data) + 1],
            "Description": [description],
            "Severity_Level": [severity],
            "Accessibility": [accessibility],
            "Address": [location],
            "Latitude": [None],
            "Longitude": [None],
            "Image_Path": [image_path]
        })
        data = pd.concat([data, new_report], ignore_index=True)
        data.to_csv(dataset_path, index=False)
        st.success("Hazard report submitted!")

# Display existing reports
st.subheader("Existing Sidewalk Hazards")
st.dataframe(data)

# Generate Actionable Proposals
st.subheader("Actionable Proposals for City")
if not data.empty:
    high_severity = data[data["Severity_Level"].isin(["High", "Severe"])]
    if not high_severity.empty:
        st.write("High-priority areas needing immediate attention:")
        
        # Allow the user to select a hazard to generate a proposal
        hazard_options = high_severity[["Hazard_ID", "Description", "Address"]].apply(
            lambda row: f"Hazard {row['Hazard_ID']} - {row['Description']} at {row['Address']}", axis=1
        )
        selected_hazard = st.selectbox("Select a hazard to generate a proposal:", options=hazard_options)
        
        if selected_hazard:
            hazard_id = int(selected_hazard.split()[1])  # Extract the Hazard ID from the selected option
            selected_row = high_severity[high_severity["Hazard_ID"] == hazard_id].iloc[0]

            # Generate proposals based on the description of the hazard
            st.write("Proposed Actions:")
            if "cracked pavement" in selected_row["Description"].lower() or "construction" in selected_row["Description"].lower():
                st.write("- **Construction Plan**: Repair damaged sidewalk sections with durable materials.")
                st.write("- **Timeline**: Approximately 2-3 weeks.")
                st.write("- **Crew Needed**: 4-6 construction workers.")
                st.write("- **Estimated Cost**: $5,000 - $7,500.")
            elif "obstacle" in selected_row["Description"].lower() or "trash" in selected_row["Description"].lower():
                st.write("- **Action**: Contact waste management to remove obstacles.")
                st.write("- **Timeline**: Within 48 hours.")
                st.write("- **Crew Needed**: 1-2 waste management workers.")
                st.write("- **Estimated Cost**: $200 - $500.")
            else:
                st.write("- **General Maintenance**: Inspect and resolve identified issues.")
                st.write("- **Timeline**: 1-2 weeks based on priority.")
                st.write("- **Crew Needed**: Variable, depending on severity.")
                st.write("- **Estimated Cost**: $1,000 - $3,000.")
else:
    st.write("No high-priority hazards reported yet.")
