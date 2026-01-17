import re

class SensitiveDataFilter:
    ... # Existing methods

    @staticmethod
    def mask_sensitive_data(text):
        # Mask Perplexity API keys
        text = re.sub(r'pplx-[a-zA-Z0-9_-]{20,}', 'pplx-***MASKED***', text)
        # Mask Pexels API key
        text = re.sub(r'PEXELS_API_KEY=\w+', '***MASKED***', text)
        return text
