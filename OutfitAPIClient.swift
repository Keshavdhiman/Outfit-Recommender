import Foundation

class OutfitAPIClient {
    private let baseURL: String
    
    init(baseURL: String) {
        self.baseURL = baseURL
    }
    
    func recommendOutfit(occasion: String, gender: String) async throws -> (outfitItems: [String], collageImage: Data?) {
        guard let url = URL(string: "\(baseURL)/analyze_audio") else {
            throw APIError.invalidURL
        }
        
        let body = ["occasion": occasion, "gender": gender]
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw APIError.invalidResponse
        }
        
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let outfitItems = json["outfit"] as? [String] else {
            throw APIError.decodingError
        }
        
        // If collage image path is provided, fetch the image data
        var collageData: Data? = nil
        if let collagePath = json["collage_image"] as? String,
           let collageURL = URL(string: "\(baseURL)/\(collagePath)") {
            let (imageData, _) = try await URLSession.shared.data(from: collageURL)
            collageData = imageData
        }
        
        return (outfitItems, collageData)
    }
}

enum APIError: Error {
    case invalidURL
    case invalidResponse
    case decodingError
}