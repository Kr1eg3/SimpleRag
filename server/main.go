package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/joho/godotenv"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Configuration for the Python RAG service
type Config struct {
	PythonRAGURL string
	Port         string
	Host         string
}

// RAG service client
type RAGClient struct {
	baseURL    string
	httpClient *http.Client
}

// Request/Response types matching Python service
type InitializeRAGRequest struct {
	DataPath     string `json:"data_path"`
	LoadExisting bool   `json:"load_existing"`
	ChunkSize    int    `json:"chunk_size"`
	ChunkOverlap int    `json:"chunk_overlap"`
}

type SearchRequest struct {
	Query string `json:"query"`
	K     int    `json:"k"`
}

type RAGResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
	Error   string `json:"error,omitempty"`
}

// Document structure from RAG API
type Document struct {
	ID             string                 `json:"id"`
	Content        string                 `json:"content"`
	Metadata       map[string]interface{} `json:"metadata"`
	SimilarityScore float64               `json:"similarity_score"`
}

// MCP Tool Input/Output structures
type InitializeRAGInput struct {
	DataPath     string `json:"data_path" jsonschema:"Path to documents directory"`
	LoadExisting bool   `json:"load_existing" jsonschema:"Load existing database if available"`
	ChunkSize    int    `json:"chunk_size" jsonschema:"Text chunk size for splitting"`
	ChunkOverlap int    `json:"chunk_overlap" jsonschema:"Overlap between chunks"`
}

type InitializeRAGOutput struct {
	Message string                 `json:"message" jsonschema:"Initialization result message"`
	Data    map[string]interface{} `json:"data,omitempty" jsonschema:"Initialization data"`
}

type SearchDocumentsInput struct {
	Query string `json:"query" jsonschema:"Search query"`
	K     int    `json:"k" jsonschema:"Number of documents to return"`
}

type SearchDocumentsOutput struct {
	Response string `json:"response" jsonschema:"Formatted response based on search results"`
}

type GetSystemStatusInput struct {
	// No input parameters needed
}

type GetSystemStatusOutput struct {
	Status map[string]interface{} `json:"status" jsonschema:"System status information"`
}

type SessionManagementInput struct {
	Action string `json:"action" jsonschema:"Action: clear_history, stats"`
}

type SessionManagementOutput struct {
	Result interface{} `json:"result" jsonschema:"Session management result"`
}

func NewRAGClient(baseURL string) *RAGClient {
	return &RAGClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *RAGClient) makeRequest(endpoint string, payload any) (*RAGResponse, error) {
	var body io.Reader
	if payload != nil {
		jsonData, err := json.Marshal(payload)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request: %w", err)
		}
		body = bytes.NewBuffer(jsonData)
	}

	req, err := http.NewRequest("POST", c.baseURL+endpoint, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var ragResp RAGResponse
	if err := json.Unmarshal(respBody, &ragResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if !ragResp.Success {
		return nil, fmt.Errorf("RAG service error: %s", ragResp.Error)
	}

	return &ragResp, nil
}

func (c *RAGClient) InitializeRAG(dataPath string, loadExisting bool, chunkSize, chunkOverlap int) (*RAGResponse, error) {
	req := InitializeRAGRequest{
		DataPath:     dataPath,
		LoadExisting: loadExisting,
		ChunkSize:    chunkSize,
		ChunkOverlap: chunkOverlap,
	}

	return c.makeRequest("/initialize", req)
}

func (c *RAGClient) SearchDocuments(query string, k int) (*RAGResponse, error) {
	req := SearchRequest{
		Query: query,
		K:     k,
	}

	return c.makeRequest("/search", req)
}

func (c *RAGClient) GetStatus() (*RAGResponse, error) {
	return c.makeRequest("/status", nil)
}

// MCP Tool implementations
func initializeRAGTool(ragClient *RAGClient) func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input InitializeRAGInput,
) (*mcp.CallToolResult, InitializeRAGOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input InitializeRAGInput,
	) (*mcp.CallToolResult, InitializeRAGOutput, error) {
		// Set defaults if not provided
		if input.DataPath == "" {
			input.DataPath = "./data"
		}
		if input.ChunkSize == 0 {
			input.ChunkSize = 1000
		}
		if input.ChunkOverlap == 0 {
			input.ChunkOverlap = 200
		}

		resp, err := ragClient.InitializeRAG(input.DataPath, input.LoadExisting, input.ChunkSize, input.ChunkOverlap)
		if err != nil {
			return nil, InitializeRAGOutput{}, err
		}

		data, _ := resp.Data.(map[string]interface{})
		return nil, InitializeRAGOutput{
			Message: resp.Message,
			Data:    data,
		}, nil
	}
}

func searchDocumentsTool(ragClient *RAGClient) func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input SearchDocumentsInput,
) (*mcp.CallToolResult, SearchDocumentsOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input SearchDocumentsInput,
	) (*mcp.CallToolResult, SearchDocumentsOutput, error) {
		if input.K == 0 {
			input.K = 5
		}

		resp, err := ragClient.SearchDocuments(input.Query, input.K)
		if err != nil {
			return nil, SearchDocumentsOutput{}, err
		}

		// Parse documents from response
		var documents []Document
		if resp.Data != nil {
			if docsData, ok := resp.Data.([]interface{}); ok {
				documents = make([]Document, 0, len(docsData))
				for _, docData := range docsData {
					if docMap, ok := docData.(map[string]interface{}); ok {
						doc := Document{
							ID:              getString(docMap, "id"),
							Content:         getString(docMap, "content"),
							SimilarityScore: getFloat64(docMap, "similarity_score"),
						}
						if metadata, ok := docMap["metadata"].(map[string]interface{}); ok {
							doc.Metadata = metadata
						}
						documents = append(documents, doc)
					}
				}
			}
		}

		// Get user_id from OAuth context (may be empty for unauthenticated requests)
		userID, _ := ctx.Value("user_id").(string)

		// Filter out chunks user has already seen (only if authenticated)
		if userID != "" && sessionManager != nil {
			originalChunkIDs := make([]string, len(documents))
			for i, doc := range documents {
				originalChunkIDs[i] = doc.ID
			}

			// Filter to get only new chunks
			newChunkIDs, err := sessionManager.FilterNewChunks(userID, originalChunkIDs)
			if err != nil {
				log.Printf("⚠️ Failed to filter chunks: %v", err)
			} else if len(newChunkIDs) < len(originalChunkIDs) {
				// Filter documents to only include new chunks
				newDocuments := make([]Document, 0)
				newChunkSet := make(map[string]bool)
				for _, id := range newChunkIDs {
					newChunkSet[id] = true
				}

				for _, doc := range documents {
					if newChunkSet[doc.ID] {
						newDocuments = append(newDocuments, doc)
					}
				}
				documents = newDocuments
			}

			// Save new chunk IDs
			if len(documents) > 0 {
				chunkIDs := make([]string, len(documents))
				for i, doc := range documents {
					chunkIDs[i] = doc.ID
				}
				if err := sessionManager.SaveChunkIDs(userID, chunkIDs); err != nil {
					log.Printf("⚠️ Failed to save chunk IDs: %v", err)
				}
			}
		}

		// Format documents into a readable response
		var response string
		if len(documents) == 0 {
			if userID != "" {
				response = "All relevant information about '" + input.Query + "' has already been provided in previous interactions. No new context chunks are available."
			} else {
				response = "No relevant documents found for the query: " + input.Query
			}
		} else {
			response = "Based on the search query '" + input.Query + "', here are the relevant findings:\n\n"
			for i, doc := range documents {
				response += fmt.Sprintf("Document %d (similarity: %.2f):\n%s\n\n", i+1, doc.SimilarityScore, doc.Content)
			}
		}

		return nil, SearchDocumentsOutput{Response: response}, nil
	}
}

func getSystemStatusTool(ragClient *RAGClient) func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input GetSystemStatusInput,
) (*mcp.CallToolResult, GetSystemStatusOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input GetSystemStatusInput,
	) (*mcp.CallToolResult, GetSystemStatusOutput, error) {
		resp, err := ragClient.GetStatus()
		if err != nil {
			return nil, GetSystemStatusOutput{}, err
		}

		status := make(map[string]interface{})
		if resp.Data != nil {
			if statusData, ok := resp.Data.(map[string]interface{}); ok {
				status = statusData
			}
		}

		// Add session stats if session manager is available
		if sessionManager != nil {
			sessionStats, err := sessionManager.GetStats()
			if err != nil {
				log.Printf("⚠️ Failed to get session stats: %v", err)
			} else {
				status["session_management"] = sessionStats
			}
		} else {
			status["session_management"] = map[string]string{"status": "not available"}
		}

		return nil, GetSystemStatusOutput{Status: status}, nil
	}
}

func sessionManagementTool() func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input SessionManagementInput,
) (*mcp.CallToolResult, SessionManagementOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input SessionManagementInput,
	) (*mcp.CallToolResult, SessionManagementOutput, error) {
		// Get user_id from OAuth context (may be empty for unauthenticated requests)
		userID, _ := ctx.Value("user_id").(string)

		switch input.Action {
		case "clear_history":
			if userID == "" {
				return nil, SessionManagementOutput{}, fmt.Errorf("user not authenticated")
			}
			if sessionManager == nil {
				return nil, SessionManagementOutput{}, fmt.Errorf("session manager not available")
			}
			err := sessionManager.ClearUserHistory(userID)
			if err != nil {
				return nil, SessionManagementOutput{}, fmt.Errorf("failed to clear history: %w", err)
			}
			result := map[string]string{
				"user_id": userID,
				"status":  "cleared",
			}
			return nil, SessionManagementOutput{Result: result}, nil

		case "stats":
			if sessionManager == nil {
				return nil, SessionManagementOutput{Result: map[string]string{"status": "session manager not available"}}, nil
			}
			stats, err := sessionManager.GetStats()
			if err != nil {
				return nil, SessionManagementOutput{}, fmt.Errorf("failed to get stats: %w", err)
			}
			return nil, SessionManagementOutput{Result: stats}, nil

		default:
			return nil, SessionManagementOutput{}, fmt.Errorf("unknown action: %s", input.Action)
		}
	}
}

// Helper functions
func getString(m map[string]interface{}, key string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

func getFloat64(m map[string]interface{}, key string) float64 {
	if val, ok := m[key]; ok {
		if f, ok := val.(float64); ok {
			return f
		}
	}
	return 0.0
}

func loadConfig() *Config {
	// Load .env file if it exists
	_ = godotenv.Load()

	config := &Config{
		PythonRAGURL: "http://127.0.0.1:8008",
		Port:         "8009",
		Host:         "127.0.0.1",
	}

	if url := os.Getenv("PYTHON_RAG_URL"); url != "" {
		config.PythonRAGURL = url
	}

	if port := os.Getenv("GO_MCP_PORT"); port != "" {
		config.Port = port
	}

	if host := os.Getenv("GO_MCP_HOST"); host != "" {
		config.Host = host
	}

	return config
}

// Global session manager and OAuth manager
var sessionManager *SimpleSessionManager
var globalOAuthManager *SimpleOAuthManager

// Helper function to check if OAuth token is expired
func isTokenExpired(token *OAuthToken) bool {
	return time.Now().After(token.CreatedAt.Add(time.Duration(token.ExpiresIn) * time.Second))
}

func main() {
	config := loadConfig()

	// Create RAG client
	ragClient := NewRAGClient(config.PythonRAGURL)

	// Initialize session manager with SQLite
	var err error
	sessionManager, err = NewSimpleSessionManager("./sessions.db")
	if err != nil {
		log.Fatal("Failed to initialize session manager:", err)
	}

	// Initialize OAuth manager
	serverAddr := config.Host + ":" + config.Port
	globalOAuthManager = NewSimpleOAuthManager(serverAddr)
	globalOAuthManager.setupEndpoints()

	// Create MCP server
	server := mcp.NewServer(&mcp.Implementation{
		Name:    "go-mcp",
		Version: "1.0.0",
	}, nil)

	// Register tools
	mcp.AddTool(server, &mcp.Tool{
		Name:        "initialize_rag",
		Description: "Initialize RAG system with documents",
	}, initializeRAGTool(ragClient))

	mcp.AddTool(server, &mcp.Tool{
		Name:        "search_documents",
		Description: "Search for similar documents and return formatted response",
	}, searchDocumentsTool(ragClient))

	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_system_status",
		Description: "Get system status",
	}, getSystemStatusTool(ragClient))

	mcp.AddTool(server, &mcp.Tool{
		Name:        "session_management",
		Description: "Manage user sessions and context history",
	}, sessionManagementTool())

	// Create MCP handler
	mcpHandler := mcp.NewStreamableHTTPHandler(func(req *http.Request) *mcp.Server {
		// Extract OAuth token and add to context
		if authHeader := req.Header.Get("Authorization"); strings.HasPrefix(authHeader, "Bearer ") {
			token := strings.TrimPrefix(authHeader, "Bearer ")
			if oauthToken, exists := globalOAuthManager.tokens[token]; exists && !isTokenExpired(oauthToken) {
				// Add user_id to request context
				ctx := context.WithValue(req.Context(), "user_id", oauthToken.UserID)
				*req = *req.WithContext(ctx)
				log.Printf("🔐 Authenticated user: %s", oauthToken.UserID)
			}
		}
		return server
	}, nil)

	// Register MCP endpoint
	http.Handle("/sse", mcpHandler)

	// Create logging middleware for all requests
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("📡 %s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)
		if r.URL.Path != "/sse" {
			http.NotFound(w, r)
		}
	})

	log.Printf("🚀 Starting Go MCP Server on http://%s", serverAddr)
	log.Printf("🐍 Python RAG Service URL: %s", config.PythonRAGURL)
	log.Printf("📋 Available tools: initialize_rag, search_documents, get_system_status, session_management")
	log.Printf("🔗 MCP endpoint: http://%s/sse", serverAddr)
	log.Printf("💡 For Claude Code: claude add http://%s/sse", serverAddr)
	log.Printf("📊 Session Management: SQLite database (./sessions.db)")
	log.Printf("🔐 OAuth 2.1 endpoints (MCP-compliant):")
	log.Printf("   GET  /.well-known/oauth-authorization-server - OAuth Discovery metadata")
	log.Printf("   GET  /.well-known/oauth-protected-resource - Protected Resource metadata")
	log.Printf("   GET  /oauth/authorize - Authorization endpoint")
	log.Printf("   POST /oauth/token - Token endpoint")
	log.Printf("   POST /register - Dynamic client registration")

	// Start the HTTP server
	if err := http.ListenAndServe(serverAddr, nil); err != nil {
		log.Fatal("Server failed:", err)
	}
}