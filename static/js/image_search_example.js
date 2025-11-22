/**
 * Qdrant Image Similarity Search - JavaScript Example
 * 
 * This example shows how to use the /api/images/search-similar endpoint
 * to find similar images using Qdrant vector search.
 */

const API_BASE_URL = 'http://localhost:8000'; // Adjust to your API URL
const SEARCH_ENDPOINT = `${API_BASE_URL}/api/images/search-similar`;

/**
 * Search for similar images by uploading a file
 * 
 * @param {File} imageFile - The image file to search for
 * @param {Object} options - Search options
 * @param {number} options.limit - Maximum number of results (default: 10)
 * @param {number} options.scoreThreshold - Minimum similarity score 0-1 (optional)
 * @returns {Promise<Object>} Search results
 */
async function searchSimilarImages(imageFile, options = {}) {
    const { limit = 10, scoreThreshold = null } = options;
    
    // Create FormData
    const formData = new FormData();
    formData.append('image_file', imageFile);
    formData.append('limit', limit.toString());
    if (scoreThreshold !== null) {
        formData.append('score_threshold', scoreThreshold.toString());
    }
    
    // Make API request
    const response = await fetch(SEARCH_ENDPOINT, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
}

/**
 * Example: Search for similar images from a file input
 */
async function exampleFromFileInput() {
    const fileInput = document.getElementById('imageFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select an image file');
        return;
    }
    
    try {
        console.log('Searching for similar images...');
        const results = await searchSimilarImages(file, {
            limit: 10,
            scoreThreshold: 0.7  // Only return images with 70%+ similarity
        });
        
        console.log('Query image description:', results.query_image);
        console.log(`Found ${results.total_found} similar images:`);
        
        results.results.forEach((result, index) => {
            // Use image_url if available (actual accessible URL), fallback to image_uri
            const imageUrl = result.image_url || result.image_uri || '';
            console.log(`${index + 1}. ${imageUrl} (score: ${result.score.toFixed(3)})`);
        });
        
        return results;
    } catch (error) {
        console.error('Error searching for similar images:', error);
        throw error;
    }
}

/**
 * Example: Search for similar images from a URL (requires downloading first)
 */
async function searchSimilarImagesFromURL(imageURL, options = {}) {
    // First, download the image
    const response = await fetch(imageURL);
    const blob = await response.blob();
    
    // Convert blob to File
    const file = new File([blob], 'image.jpg', { type: blob.type });
    
    // Search using the file
    return await searchSimilarImages(file, options);
}

/**
 * Example: React component usage
 */
function ImageSearchComponent() {
    const [results, setResults] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);
    
    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        setLoading(true);
        setError(null);
        
        try {
            const searchResults = await searchSimilarImages(file, {
                limit: 10,
                scoreThreshold: 0.6
            });
            setResults(searchResults);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <input type="file" accept="image/*" onChange={handleFileChange} />
            {loading && <p>Searching...</p>}
            {error && <p style={{color: 'red'}}>Error: {error}</p>}
            {results && (
                <div>
                    <h3>Found {results.total_found} similar images</h3>
                    <p>Query: {results.query_image}</p>
                    <div className="results-grid">
                        {results.results.map((result, index) => (
                            <div key={index} className="result-card">
                                <img src={result.image_url || result.image_uri || ''} alt={`Result ${index + 1}`} />
                                <p>Similarity: {(result.score * 100).toFixed(1)}%</p>
                                <p>{result.image_url || result.image_uri || 'No URL available'}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        searchSimilarImages,
        searchSimilarImagesFromURL
    };
}

