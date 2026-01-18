import logging
import html

# Initialize logging
logging.basicConfig(level=logging.DEBUG)

def fetch_images(image_urls):
    sanitized_urls = []
    for url in image_urls:
        # Sanitize the URL
        sanitized_url = html.unescape(url)
        logging.debug(f'Sanitized URL: {sanitized_url}')
        sanitized_urls.append(sanitized_url)
    return sanitized_urls
