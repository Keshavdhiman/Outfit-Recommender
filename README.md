# Outfit Recommender API

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn main:app`
   - Python Version: 3.9.0

## iOS Integration

1. Add `OutfitAPIClient.swift` to your iOS project
2. Initialize the client with your Render deployment URL:
```swift
let apiClient = OutfitAPIClient(baseURL: "https://your-render-url.onrender.com")
```

3. Call the API:
```swift
Task {
    do {
        let (outfitItems, collageImage) = try await apiClient.recommendOutfit(
            occasion: "casual",
            gender: "male"
        )
        // Handle the response
    } catch {
        // Handle errors
    }
}
```

## Environment Setup

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```