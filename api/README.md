# API Documentation

This is the Express API server for the AI Content Telegram Bot project.

## Setup

1. Navigate to the `/api` directory:
```bash
cd api
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit the `.env` file to configure your MongoDB connection:
```
MONGODB_URI=mongodb://localhost:27017/ai-content-bot
PORT=3000
```

## Running the Server

Start the server:
```bash
npm start
```

The server will run on port 3000 by default.

## API Endpoints

### Health Check
- **GET** `/health`
- Returns server status

**Response:**
```json
{
  "status": "ok",
  "message": "Server is running",
  "timestamp": "2026-01-10T19:36:04.125Z"
}
```

### Clothes
- **GET** `/clothes`
- Returns a list of clothes items

**Response:**
```json
[
  {
    "id": 1,
    "name": "Classic T-Shirt",
    "category": "Tops",
    "size": "M",
    "color": "Blue",
    "price": 29.99,
    "description": "Comfortable cotton t-shirt",
    "inStock": true
  }
]
```

## Models

### Clothes Schema
The Clothes model includes the following fields:
- `name` (String, required)
- `category` (String, required)
- `size` (String, optional)
- `color` (String, optional)
- `price` (Number, optional)
- `description` (String, optional)
- `inStock` (Boolean, default: true)
- `timestamps` (automatic createdAt/updatedAt)

## Dependencies

- **express** - Web framework
- **cors** - CORS middleware
- **dotenv** - Environment variable management
- **mongoose** - MongoDB ODM

## Notes

- If MongoDB is not available, the `/clothes` endpoint will return default mock data
- The server uses CORS middleware to allow cross-origin requests
- All routes use JSON format for request/response bodies
