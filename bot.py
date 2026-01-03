import logging
import requests

# Set up logging with appropriate level and formatting
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Example tokens for demonstration purposes
    TELEGRAM_TOKEN = "example_telegram_token"
    PERPLEXITY_API_KEY = "example_perplexity_api_key"

    try:
        # Verify Telegram token presence
        logging.debug("Verifying presence of TELEGRAM_TOKEN.")
        if not TELEGRAM_TOKEN:
            raise ValueError("Missing TELEGRAM_TOKEN. Ensure it is set correctly.")

        # Verify Perplexity API token presence
        logging.debug("Verifying presence of PERPLEXITY_API_KEY.")
        if not PERPLEXITY_API_KEY:
            raise ValueError("Missing PERPLEXITY_API_KEY. Ensure it is set correctly.")

    except ValueError as e:
        logging.error(f"Token verification failed: {e}")
        return

    try:
        # Example URL for Perplexity API
        api_url = "https://api.perplexity.ai/query"
        payload = {"question": "example question"}
        headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}"}

        # Log API request payload
        logging.debug(f"Sending request to Perplexity API. Payload: {payload}")

        response = requests.post(api_url, json=payload, headers=headers)

        # Log API response 
        logging.debug(f"Received response from Perplexity API. Status Code: {response.status_code}, Body: {response.text}")

        if response.status_code != 200:
            raise requests.HTTPError(f"Unexpected status code {response.status_code}.")

        api_data = response.json()

        # Log parsed API data
        logging.debug(f"Parsed data from Perplexity API: {api_data}")

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request error: {e}")

    except ValueError as e:
        logging.error(f"Failed to parse API response JSON: {e}")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    logging.info("Execution completed successfully.")

if __name__ == "__main__":
    main()