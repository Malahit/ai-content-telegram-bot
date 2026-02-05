# AI Content Mobile App

This is a React Native mobile application for browsing clothing items from the AI Content Telegram Bot API.

## Features

- **Home Screen**: Displays a list of clothing items fetched from the API
- **Detail Screen**: Shows detailed information about a selected clothing item
- **Mock Images**: Uses picsum.photos placeholder images for clothing items
- **Navigation**: Implements React Navigation for seamless screen transitions

## Prerequisites

Before running the application, ensure you have the following installed:

- Node.js (v14 or higher)
- npm or yarn
- React Native CLI
- Android Studio (for Android) or Xcode (for iOS)
- An Android emulator or iOS simulator

## Installation

1. Navigate to the mobile directory:
   ```bash
   cd mobile
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. For iOS (macOS only), install CocoaPods dependencies:
   ```bash
   cd ios
   pod install
   cd ..
   ```

## Running the App

### Android

1. Start an Android emulator or connect an Android device
2. Run the following command:
   ```bash
   npx react-native run-android
   ```

### iOS (macOS only)

1. Start an iOS simulator or connect an iOS device
2. Run the following command:
   ```bash
   npx react-native run-ios
   ```

## API Configuration

The app is configured to fetch data from `http://localhost:3000/clothes` by default.

If the API is not available, the app will display mock data for demonstration purposes.

### Changing the API Endpoint

To connect to a different API endpoint, modify the `config.js` file:

```javascript
export const API_CONFIG = {
  BASE_URL: 'https://your-api-url.com',  // Change this URL
  ENDPOINTS: {
    CLOTHES: '/clothes',
  },
  TIMEOUT: 10000,
};
```

### Image Placeholders

The app uses picsum.photos for placeholder images. To use a different service, modify `config.js`:

```javascript
export const IMAGE_CONFIG = {
  BASE_URL: 'https://your-image-service.com',
  SIZES: {
    THUMBNAIL: '300/200',
    DETAIL: '400/300',
  },
};
```

## Testing

Run the Jest test suite:

```bash
npm test
```

Run tests with coverage:

```bash
npm test -- --coverage
```

## Linting

Run ESLint to check code quality:

```bash
npm run lint
```

## Project Structure

```
mobile/
├── __tests__/          # Test files
│   ├── App.test.js
│   ├── HomeScreen.test.js
│   └── DetailScreen.test.js
├── screens/            # Screen components
│   ├── HomeScreen.js
│   └── DetailScreen.js
├── App.js             # Main app component with navigation
├── index.js           # Entry point
├── package.json       # Dependencies and scripts
└── babel.config.js    # Babel configuration
```

## Troubleshooting

### Metro Bundler Issues

If you encounter issues with the Metro bundler:

```bash
npm start -- --reset-cache
```

### Build Errors

Clean the build:

```bash
# Android
cd android && ./gradlew clean && cd ..

# iOS
cd ios && xcodebuild clean && cd ..
```

### Port Already in Use

If port 8081 is already in use:

```bash
npm start -- --port 8082
```

## Future Enhancements

- Add user authentication
- Implement shopping cart functionality
- Add filters and search capabilities
- Integrate payment processing
- Add product reviews and ratings
