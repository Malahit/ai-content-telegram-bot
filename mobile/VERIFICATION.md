# Mobile App Verification Guide
 
This document provides instructions for verifying the mobile application functionality.
 
## Prerequisites Verification
 
Before running the app, ensure you have:
 
1. **Node.js and npm**
   ```bash
   node --version  # Should be v14 or higher
   npm --version
   ```
 
2. **React Native CLI**
   ```bash
   npm install -g react-native-cli
   ```
 
3. **Android Studio** (for Android) or **Xcode** (for iOS on macOS)
 
## Installation Steps
 
1. Navigate to the mobile directory:
   ```bash
   cd /path/to/ai-content-telegram-bot/mobile
   ```
 
2. Install dependencies:
   ```bash
   npm install
   ```
   
   This will install:
   - `react-native`: Core framework
   - `@react-navigation/native`: Navigation library
   - `@react-navigation/native-stack`: Stack navigator
   - `axios`: HTTP client for API calls
   - Testing libraries: Jest, React Testing Library
   - Development dependencies: Babel, ESLint, Metro
 
## Running Tests
 
### Unit Tests
 
Run all tests:
```bash
npm test
```
 
Run tests with coverage:
```bash
npm test -- --coverage
```
 
Expected output:
- All tests should pass
- Coverage should show tests for App, HomeScreen, and DetailScreen
 
### Linting
 
Check code quality:
```bash
npm run lint
```
 
## Running the Application
 
### Android Emulator
 
1. **Start Android Studio** and open AVD Manager
2. **Launch an Android Virtual Device** (AVD)
3. **Run the app**:
   ```bash
   npx react-native run-android
   ```
 
4. **Expected behavior**:
   - Metro bundler starts on port 8081
   - App builds and installs on the emulator
   - App launches and shows "Clothing Store" screen
   - If API at `http://localhost:3000/clothes` is not available, app displays mock data
 
### iOS Simulator (macOS only)
 
1. **Install CocoaPods dependencies**:
   ```bash
   cd ios
   pod install
   cd ..
   ```
 
2. **Run the app**:
   ```bash
   npx react-native run-ios
   ```
 
3. **Expected behavior**:
   - App builds and launches in iOS Simulator
   - Shows "Clothing Store" screen with clothing items
 
## Feature Verification Checklist
 
### ✅ Home Screen
- [ ] Displays loading indicator while fetching data
- [ ] Shows list of clothing items in a FlatList
- [ ] Each item shows:
  - [ ] Image from Pexels placeholder
  - [ ] Item name
  - [ ] Category
  - [ ] Price
- [ ] Tapping an item navigates to Detail screen
- [ ] Falls back to mock data if API fails
 
### ✅ Detail Screen
- [ ] Displays larger image of the item
- [ ] Shows item name, category, and price
- [ ] Displays item description
- [ ] Has "Add to Cart" button (visual only, not functional)
 
### ✅ Navigation
- [ ] Navigation header shows "Clothing Store" on Home screen
- [ ] Navigation header shows "Item Details" on Detail screen
- [ ] Back button works to return to Home screen
- [ ] Header has blue background (#2196F3)
- [ ] Header text is white
 
### ✅ API Integration
- [ ] App attempts to fetch from `http://localhost:3000/clothes`
- [ ] Displays API data if available
- [ ] Shows alert and mock data if API fails
- [ ] Uses axios for HTTP requests
 
### ✅ Images
- [ ] Uses Pexels placeholders: `https://api.pexels.com/v1` 
- [ ] Home screen images: 300x200 pixels
- [ ] Detail screen images: 400x300 pixels
- [ ] Images include category and fashion keywords
 
## Mock Data Structure
 
The app expects data in this format:
 
```json
[
  {
    "id": 1,
    "name": "Classic T-Shirt",
    "price": 29.99,
    "category": "Shirts",
    "description": "Comfortable cotton t-shirt"
  }
]
```
 
## Troubleshooting
 
### Metro Bundler Won't Start
```bash
npm start -- --reset-cache
```
 
### Build Errors
```bash
# Clean Android build
cd android && ./gradlew clean && cd ..
 
# Clean iOS build (macOS only)
cd ios && xcodebuild clean && cd ..
```
 
### Port 8081 Already in Use
```bash
# Kill process on port 8081
lsof -ti:8081 | xargs kill -9
 
# Or start on different port
npm start -- --port 8082
```
 
### Dependencies Not Installing
```bash
# Clear npm cache
npm cache clean --force
 
# Remove node_modules and reinstall
rm -rf node_modules
npm install
```
 
## CI/CD Verification
 
The GitHub Actions workflow (`.github/workflows/mobile.yml`) runs:
 
1. **Setup**: Installs Node.js 18.x
2. **Dependencies**: Runs `npm install`
3. **Tests**: Runs `npm test -- --coverage --watchAll=false`
4. **Linting**: Runs `npm run lint`
5. **Coverage**: Uploads coverage reports to Codecov
 
Trigger the workflow by:
- Pushing to `main` or `develop` branches
- Creating a PR to `main` or `develop` branches
- Only runs when files in `mobile/**` are changed
 
## Success Criteria
 
The implementation is considered successful when:
 
1. ✅ Mobile app structure is created in `/mobile` directory
2. ✅ `package.json` includes all required dependencies
3. ✅ `App.js` implements navigation between Home and Detail screens
4. ✅ Home screen uses FlatList and axios to fetch/display clothes
5. ✅ Detail screen shows item details
6. ✅ Pexels placeholders are used for images
7. ✅ App runs on Android/iOS emulator
8. ✅ All Jest tests pass
9. ✅ GitHub workflow is configured for CI/CD
10. ✅ Code is committed and pushed to repository
 
## Next Steps
 
Potential enhancements:
- Connect to actual backend API
- Implement shopping cart functionality
- Add user authentication
- Implement search and filter features
- Add animations and transitions
- Support dark mode
- Add offline support
- Implement pull-to-refresh