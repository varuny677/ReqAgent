import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

api_key = os.getenv('GOOGLE_API_KEY')
print(f"Testing API Key: {api_key[:20]}...")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

    # Simple test prompt
    response = model.generate_content("Say 'API key is working' if you can read this.")

    print("\nSUCCESS! API Key is working.")
    print(f"Response: {response.text}")

except Exception as e:
    print("\nERROR: API Key test failed")
    print(f"Error: {str(e)}")
