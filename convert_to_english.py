# convert_to_english.py
import os
import google.generativeai as genai
import absl.logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Abseil logging to suppress warnings
absl.logging.set_verbosity(absl.logging.ERROR)
absl.logging.set_stderrthreshold(absl.logging.ERROR)

# Set up your API key from environment variable
GOOGLE_API_KEY = os.environ.get('GOOGLE_LANGUAGE_API_KEY', '')

# Check if API key is available
if not GOOGLE_API_KEY:
    print("Warning: Google Language API key is missing. Please check your .env file.")

# Configure the API
genai.configure(api_key=GOOGLE_API_KEY)

# Load the desired model
model = genai.GenerativeModel("gemini-2.0-flash")

def translation(query):
    prompt = f"Convert this '{query}' to English language."
    response = model.generate_content(prompt, stream=True)
    translation = ""
    for chunk in response:
        translation += chunk.text
    return translation.strip()
