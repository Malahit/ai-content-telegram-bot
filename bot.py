def generate_content(prompt):
    import requests

    # Base URL for Perplexity API
    api_url = "https://api.perplexity.ai/generate"

    # Headers for the API request
    headers = {
        "Authorization": "Bearer your_api_key_here",  # Replace with valid API key
        "Content-Type": "application/json"
    }

    # Payload for the API request (Adapt as per Perplexity's API schema)
    data = {
        "prompt": prompt
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if 'content' in result:
            return result['content']
        else:
            raise ValueError("Invalid response format received from Perplexity API.")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Request to Perplexity API failed: {e}")

    except ValueError as e:
        raise RuntimeError(f"Error processing the Perplexity API response: {e}")