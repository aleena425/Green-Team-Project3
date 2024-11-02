# app.py
import pandas as pd
import streamlit as st
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing.image import img_to_array

# Load the sidewalk hazards dataset
dataset_path = "sidewalk_hazards.csv"  # Ensure this CSV file is in the same directory as app.py
data = pd.read_csv(dataset_path)

# Define color mapping for mood
mood_to_color = {
    "Easily Accessible": "#DFF2BF",
    "Moderately Accessible": "#BDE5F8",
    "Not Accessible": "#FFD2D2",
    "Challenging": "#FFF2CC"
}

# Mood selection
st.title("Mood to Color Accessibility Feature")
mood = st.selectbox("Select your mood:", options=list(mood_to_color.keys()))

# Set background color based on mood
st.markdown(
    f"""
    <style>
    .reportview-container {{
        background-color: {mood_to_color[mood]};
    }}
    </style>
    """, unsafe_allow_html=True
)
st.write(f"The background color has been set to match your mood: {mood}")

# Hazard Reporting
st.title("Report a Sidewalk Hazard")
st.subheader("Existing Sidewalk Hazards")
st.dataframe(data)

# Hazard Reporting
st.title("Report a Sidewalk Hazard")

with st.form("report_form"):
    description = st.text_input("Describe the hazard")
    severity = st.selectbox("Select severity level", ["Low", "Moderate", "High", "Severe"])
    accessibility = st.selectbox("Select Accessibility Level", ["Easily Accessible", "Moderately Accessible", "Challenging", "Not Accessible"])
    location = st.text_input("Location (address or coordinates)")
    submitted = st.form_submit_button("Submit Report")

    if submitted:
        # Append new report to the DataFrame
        new_data = pd.DataFrame({
            "Hazard_ID": [len(data) + 1],
            "Description": [description],
            "Severity_Level": [severity],
            "Accessibility": [accessibility],
            "Address": [location],
            "Latitude": [None],  # Placeholder if no specific latitude provided
            "Longitude": [None], # Placeholder if no specific longitude provided
            "Image_Path": [None]  # Placeholder if no image path provided
        })
        
        data = pd.concat([data, new_data], ignore_index=True)
        
        # Save updated dataset to CSV
        data.to_csv(dataset_path, index=False)
        
        st.success("Hazard report submitted!")
        st.write(new_data)  # Display the new entry


# Load pre-trained model
model = MobileNetV2(weights="imagenet")

st.title("Upload an Image of an Obstacle")

uploaded_image = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
if uploaded_image:
    # Open the uploaded image and convert to RGB if needed
    image = Image.open(uploaded_image).convert("RGB")  # Ensure 3 color channels (RGB)
    
    # Display the original uploaded image
    st.image(image, caption="Uploaded Image", use_column_width=True)
    
    # Resize the image to 224x224 for the model
    image = image.resize((224, 224))  # Resize to the input size expected by MobileNetV2
    
    # Preprocess image for MobileNetV2
    img_array = img_to_array(image)
    img_array = preprocess_input(img_array)
    img_array = img_array.reshape((1, 224, 224, 3))

    # Predict and display results
    predictions = model.predict(img_array)
    results = decode_predictions(predictions, top=3)[0]
    st.write("Predictions:")
    for label, description, probability in results:
        st.write(f"{description}: {probability * 100:.2f}%")
