import openai
import streamlit as st
import folium
from streamlit_folium import st_folium
import googlemaps
import polyline
import requests
from datetime import datetime, timedelta
import random
import pandas as pd
from PIL import Image
import os
import re
from gtts import gTTS


# Set up OpenAI API key
openai.api_key = "API_KEY_HERE"  # Replace with your actual API key


# Initialize Google Maps client
API_KEY = "GOOGLE_API_KEY"  # Replace with your actual Google API key
gmaps = googlemaps.Client(key=API_KEY)


# Sidewalk safety and accessibility color mapping
accessibility_colors = {
    "Easily Accessible": "#32CD32",
    "Moderately Accessible": "#1E90FF",
    "Challenging": "#FFD700",
    "Inaccessible": "#FF6347"
}


# Hazard status mapping with icons
status_icons = {
    "Not Started": "🟠 Not Started",
    "In Progress": "🟡 In Progress",
    "Completed": "🟢 Completed"
}


# Dataset path for storing reports
dataset_path = "sidewalk_hazards.csv"


# Load or create the hazards dataset
def load_data():
    try:
        data = pd.read_csv(dataset_path)
    except FileNotFoundError:
        data = pd.DataFrame(columns=["Hazard_ID", "Description", "Severity_Level", "Accessibility", "Address", "Image_Path", "Date", "Time", "Status"])
    return data


data = load_data()


# Function to generate a detailed project plan including the number of people needed and budget estimate
def generate_project_plan_and_budget(hazard_description):
    try:
        prompt = f"""
        Generate a detailed project plan for resolving the following sidewalk hazard:
        Hazard: {hazard_description}
        
        The plan should include:
        1. A description of actions.
        2. A timeline.
        3. Required people.
        4. Equipment or materials needed.
        5. An estimated budget.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        project_plan = response['choices'][0]['message']['content'].strip()
        estimated_budget = None
        if "estimated budget" in project_plan.lower():
            start_idx = project_plan.lower().find("estimated budget")
            budget_text = project_plan[start_idx:]
            budget_start = budget_text.find("$")
            if budget_start != -1:
                budget_end = budget_text.find("USD", budget_start)
                if budget_end != -1:
                    estimated_budget = budget_text[budget_start:budget_end].strip()
        
        return project_plan, estimated_budget
    except Exception as e:
        return f"Error generating project plan: {e}", None


# Function to autocomplete places
def autocomplete_places(input_text):
    autocomplete_url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={input_text}&key={API_KEY}"
    try:
        response = requests.get(autocomplete_url)
        response.raise_for_status()
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
            
            synthetic_route = []
            route_reasons = []
            for point in decoded_route:
                accessibility_level = random.choice(list(accessibility_colors.keys()))
                synthetic_route.append((point, accessibility_level))
                reason = random.choice([
                    "The original route had a road closure due to construction, and this route avoids the blocked area.",
                    "Uneven pavement was present along the original route, so this alternate path is safer for you.",
                    "There was a major pothole in the original route, so this route is smoother and safer.",
                    "A vehicle accident caused a blockage on the original route, so this new route avoids the area.",
                    "The original sidewalk was under repair, making it inaccessible, so this route is an alternative.",
                    "The original route had flooding, so this route is a better option for walking."
                ]) if random.random() < 0.5 else None
                route_reasons.append(reason)
            
            st.session_state['route'] = synthetic_route
            st.session_state['duration'] = route["legs"][0]["duration"]["value"]
            st.session_state['steps'] = route["legs"][0]["steps"]
            st.session_state['reasons'] = route_reasons
        else:
            st.error("No route found. Please check the start and end locations.")
    except googlemaps.exceptions.ApiError as e:
        st.error(f"Google Maps API Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")


# Function to convert text to speech and play it in Streamlit
def speak_text(text, filename="route_instructions.mp3"):
    try:
        # Clean the text by removing HTML tags and extra spaces
        cleaned_text = re.sub(r'<[^>]*>', '', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Convert text to speech and save it as an MP3 file
        tts = gTTS(cleaned_text)
        tts.save(filename)
        
        # Open the saved MP3 file and read it as bytes
        audio_file = open(filename, "rb")
        audio_bytes = audio_file.read()
        st.audio(audio_bytes, format="audio/mp3")
        audio_file.close()
        os.remove(filename)  # Remove the file after playing to save space
    except gTTS.tts.gTTSError as e:
        # Handle the Too Many Requests error gracefully
        st.error("Text-to-speech is currently unavailable due to usage limits. Please try again later.")
        print(f"gTTS Error: {e}")


# Function to display reports table with images
def display_report_table(dataframe):
    dataframe["Status"] = dataframe["Status"].apply(lambda x: status_icons.get(x, x))
    st.dataframe(dataframe[["Hazard_ID", "Description", "Severity_Level", "Accessibility", "Address", "Date", "Time", "Status", "Image_Path"]])


# Start of Tabs
tab1, tab2, tab3 = st.tabs(["Route", "Hazard Reporting and Management", "Actionable Proposals"])


# Tab 1: Route
with tab1:
    st.title("Route Map, Directions, and Sidewalk Safety Information for Pedestrians")
    
    if 'start_location' not in st.session_state:
        st.session_state.start_location = ""
    if 'end_location' not in st.session_state:
        st.session_state.end_location = ""


    start_location_input = st.text_input("Enter the start location:", value=st.session_state.start_location)
    if start_location_input:
        autocomplete_results = autocomplete_places(start_location_input)
        if autocomplete_results.get("predictions"):
            st.write("Suggestions:")
            for prediction in autocomplete_results["predictions"]:
                if st.button(prediction['description'], key=f"start-{prediction['place_id']}"):
                    st.session_state.start_location = prediction['description']


    end_location_input = st.text_input("Enter the end location:", value=st.session_state.end_location)
    if end_location_input:
        autocomplete_results = autocomplete_places(end_location_input)
        if autocomplete_results.get("predictions"):
            st.write("Suggestions:")
            for prediction in autocomplete_results["predictions"]:
                if st.button(prediction['description'], key=f"end-{prediction['place_id']}"):
                    st.session_state.end_location = prediction['description']


    if st.button("Get Route Information"):
        fetch_route_info()


    if 'route' in st.session_state:
        route_data = st.session_state['route']
        duration_text = str(timedelta(seconds=st.session_state['duration']))
        steps = st.session_state['steps']
        route_reasons = st.session_state['reasons']


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


        st.subheader("Color-Coded Key for Accessibility Levels")
        st.write(f"""
            <span style="color: #32CD32;">- **Green (Easily Accessible):**</span> Safe, smooth, and easy-to-navigate sidewalks. <br>
            <span style="color: #1E90FF;">- **Blue (Moderately Accessible):**</span> Sidewalks with minor obstacles but generally walkable. <br>
            <span style="color: #FFD700;">- **Yellow (Challenging):**</span> Sidewalks with significant obstacles or uneven surfaces. <br>
            <span style="color: #FF6347;">- **Red (Inaccessible):**</span> Sidewalks that are not passable due to major obstacles or damage.
        """, unsafe_allow_html=True)


        st.subheader("Step-by-Step Directions with Reasons for Route Selection")
        for i, (step, reason) in enumerate(zip(steps, route_reasons), 1):
            distance = step["distance"]["text"]
            duration = step["duration"]["text"]
            instructions = step["html_instructions"]
            st.markdown(f"**Step {i}:** {instructions} - **{distance}**, ~{duration}", unsafe_allow_html=True)
            if reason:
                st.write(f"**Reason for this part of the route:** {reason}")
            tts_text = f"Step {i}: {instructions}. Estimated distance is {distance}, and estimated time is {duration}."
            if reason:
                tts_text += f" The original route had an issue: {reason}. This route is better for you."
            speak_text(tts_text)


# Tab 2: Hazard Reporting, Display Reports with Image Column, and Manage Report Status
with tab2:
    st.subheader("Report a Sidewalk Hazard")
    
    # Form to handle hazard report submission
    with st.form("report_form"):
        description = st.text_input("Describe the hazard")
        severity = st.selectbox("Select severity level", ["Low", "Moderate", "High", "Severe"])
        accessibility = st.selectbox("Accessibility Level", list(accessibility_colors.keys()))
        location = st.text_input("Location (address or coordinates)")
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Submit Report")
    
    # Check if form is submitted and handle the hazard report submission
    if submitted:
        if not description or not severity or not accessibility or not location:
            st.error("Please fill out all required fields (Description, Severity Level, Accessibility Level, and Location).")
        else:
            image_path = None
            if uploaded_image:
                image_dir = "uploaded_images"
                if not os.path.exists(image_dir):
                    os.makedirs(image_dir)
                image_path = os.path.join(image_dir, uploaded_image.name)
                Image.open(uploaded_image).convert("RGB").save(image_path)
            
            # Add report data and save it
            date_of_report = datetime.now().strftime("%Y-%m-%d")
            time_of_report = datetime.now().strftime("%H:%M:%S")
            new_report = pd.DataFrame({
                "Hazard_ID": [len(data) + 1],
                "Description": [description],
                "Severity_Level": [severity],
                "Accessibility": [accessibility],
                "Address": [location],
                "Image_Path": [image_path],
                "Date": [date_of_report],
                "Time": [time_of_report],
                "Status": ["Not Started"]
            })
            
            # Ensure no duplicate reports
            if not ((data["Description"] == description) & (data["Address"] == location)).any():
                data = pd.concat([data, new_report], ignore_index=True)
                data.to_csv(dataset_path, index=False)
                data = load_data()  # Reload data after saving
                st.success("Hazard report submitted!")
            else:
                st.warning("This hazard has already been reported.")
    
    # Display reports with images column
    st.subheader("Current Sidewalk Hazards")
    current_hazards = data[data["Status"].isin(["Not Started", "In Progress"])]
    archived_hazards = data[data["Status"] == "Completed"]


    st.subheader("Current Hazards")
    display_report_table(current_hazards)
    
    st.subheader("Archived Hazards")
    display_report_table(archived_hazards)
    
    # Manage report status section
    st.subheader("Manage Report Status")
    report_options = data["Hazard_ID"].astype(str) + " - " + data["Description"]
    selected_report = st.selectbox("Select Report", options=report_options, key="selected_report")
    
    # Handle report status change
    if selected_report:
        selected_hazard_id = int(selected_report.split(" - ")[0])
        new_status = st.selectbox("Change Status for Selected Report", ["Not Started", "In Progress", "Completed"], key="new_status")
        
        if st.button("Update Status"):
            data.loc[data["Hazard_ID"] == selected_hazard_id, "Status"] = new_status
            data.to_csv(dataset_path, index=False)
            data = load_data()  # Reload data after updating
            st.success("Status updated successfully!")


# Tab 3: Actionable Proposals
with tab3:
    st.subheader("Actionable Proposals for City")
    hazard_options = data[["Hazard_ID", "Description", "Address"]].apply(
        lambda row: f"Hazard {row['Hazard_ID']} - {row['Description']} at {row['Address']}", axis=1
    )
    selected_hazard = st.selectbox("Select a hazard to generate a proposal:", options=hazard_options)


    if selected_hazard:
        hazard_id = int(selected_hazard.split()[1])
        selected_row = data[data["Hazard_ID"] == hazard_id].iloc[0]


        st.write("Proposed Actions:")
        hazard_description = selected_row["Description"]


        project_plan, estimated_budget = generate_project_plan_and_budget(hazard_description)
        st.write(project_plan)


        if estimated_budget:
            st.subheader("Estimated Budget")
            st.write(f"The estimated budget to fix this issue is {estimated_budget}.")
