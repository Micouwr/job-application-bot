"""
Standalone test script to verify successful connection, authentication, 
and generation using the google-genai SDK and the GEMINI_API_KEY from .env.
"""
import os
import sys
import logging
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    from google.generativeai.errors import APIError
except ImportError:
    print("Error: The 'google-genai' package is not installed.")
    sys.exit(1)

# Configure logging for better output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gemini_connection():
    """
    Attempts to configure the API and generate content to verify connectivity.
    """
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)

    try:
        # 2. Configure the client
        genai.configure(api_key=api_key)
        
        # 3. Use the specified model (Updated to 2.5)
        model_name = "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name)
        
        logger.info(f"Attempting connection with model: {model_name}...")

        # 4. Generate content
        prompt = "Say 'Gemini is working!' in a fun and brief way."
        response = model.generate_content(prompt)
        
        # 5. Print result
        print("\n=== Gemini API Test Successful ===")
        print(f"Prompt: {prompt}")
        print(f"Response: {response.text.strip()}")
        print("================================\n")

    except APIError as e:
        logger.error(f"Gemini API Error: Check your API key or permissions.")
        logger.error(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during API call: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_gemini_connection()