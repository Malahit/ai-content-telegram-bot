// API Configuration
export const API_CONFIG = {
  // Base URL for the clothes API
  // Change this for different environments (development, staging, production)
  BASE_URL: 'http://localhost:3000',
  
  // API Endpoints
  ENDPOINTS: {
    CLOTHES: '/clothes',
  },
  
  // Timeout for API requests (in milliseconds)
  TIMEOUT: 10000,
};

// Placeholder image service
// Using picsum.photos as a reliable alternative to deprecated placeholder services
export const IMAGE_CONFIG = {
  // Base URL for placeholder images
  BASE_URL: 'https://picsum.photos',
  
  // Image sizes
  SIZES: {
    THUMBNAIL: '300/200',
    DETAIL: '400/300',
  },
};
