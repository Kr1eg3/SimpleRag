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
	ExternalHost string // External accessible address for OAuth callbacks
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
	Query        string `json:"query"`
	K            int    `json:"k"`
	DatabaseName string `json:"database_name"`
}

type RAGResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
	Error   string `json:"error,omitempty"`
}

// Document structure from RAG API
type Document struct {
	ID              string                 `json:"id"`
	Content         string                 `json:"content"`
	Metadata        map[string]any `json:"metadata"`
	SimilarityScore float64                `json:"similarity_score"`
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
	Data    map[string]any `json:"data,omitempty" jsonschema:"Initialization data"`
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
	Status map[string]any `json:"status" jsonschema:"System status information"`
}

type SessionManagementInput struct {
	Action string `json:"action" jsonschema:"Action: clear_history, stats"`
}

type SessionManagementOutput struct {
	Result any `json:"result" jsonschema:"Session management result"`
}

type SwitchDatabaseInput struct {
	DatabaseName string `json:"database_name" jsonschema:"Name of the database to switch to"`
}

type SwitchDatabaseOutput struct {
	Message      string `json:"message" jsonschema:"Result message"`
	DatabaseName string `json:"database_name" jsonschema:"Active database name"`
}

type ListDatabasesInput struct {
	// No input needed
}

type ListDatabasesOutput struct {
	Databases []map[string]any `json:"databases" jsonschema:"List of available databases"`
	Count     int              `json:"count" jsonschema:"Number of databases"`
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

func (c *RAGClient) SearchDocuments(query string, k int, databaseName string) (*RAGResponse, error) {
	req := SearchRequest{
		Query:        query,
		K:            k,
		DatabaseName: databaseName,
	}

	return c.makeRequest("/search", req)
}

func (c *RAGClient) ListDatabases() (*RAGResponse, error) {
	req, err := http.NewRequest("GET", c.baseURL+"/list_databases", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
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

		data, _ := resp.Data.(map[string]any)
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

		// Get user_id from OAuth context (may be empty for unauthenticated requests)
		userID, _ := ctx.Value(userIDKey).(string)

		// Get user's active database
		databaseName := "default"
		if userID != "" && sessionManager != nil {
			if dbName, err := sessionManager.GetUserActiveDatabase(userID); err == nil && dbName != "" {
				databaseName = dbName
			}
		}

		resp, err := ragClient.SearchDocuments(input.Query, input.K, databaseName)
		if err != nil {
			return nil, SearchDocumentsOutput{}, err
		}

		// Parse documents from response
		var documents []Document
		if resp.Data != nil {
			if docsData, ok := resp.Data.([]any); ok {
				documents = make([]Document, 0, len(docsData))
				for _, docData := range docsData {
					if docMap, ok := docData.(map[string]any); ok {
						doc := Document{
							ID:              getString(docMap, "id"),
							Content:         getString(docMap, "content"),
							SimilarityScore: getFloat64(docMap, "similarity_score"),
						}
						if metadata, ok := docMap["metadata"].(map[string]any); ok {
							doc.Metadata = metadata
						}
						documents = append(documents, doc)
					}
				}
			}
		}

		// Save original documents for logging (before filtering)
		originalDocuments := documents

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

		// Save search log if user is authenticated and session manager is available
		if userID != "" && sessionManager != nil {
			// Prepare RAG response (original documents before filtering, as JSON)
			ragResponseJSON, _ := json.Marshal(originalDocuments)
			ragResponseStr := string(ragResponseJSON)

			// Save the search log
			if err := sessionManager.SaveSearchLog(userID, input.Query, ragResponseStr, response); err != nil {
				log.Printf("⚠️ Failed to save search log: %v", err)
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

		status := make(map[string]any)
		if resp.Data != nil {
			if statusData, ok := resp.Data.(map[string]any); ok {
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
		userID, _ := ctx.Value(userIDKey).(string)

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

func switchDatabaseTool(ragClient *RAGClient) func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input SwitchDatabaseInput,
) (*mcp.CallToolResult, SwitchDatabaseOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input SwitchDatabaseInput,
	) (*mcp.CallToolResult, SwitchDatabaseOutput, error) {
		// Get user_id from OAuth context
		userID, _ := ctx.Value(userIDKey).(string)
		if userID == "" {
			return nil, SwitchDatabaseOutput{}, fmt.Errorf("user not authenticated")
		}

		if sessionManager == nil {
			return nil, SwitchDatabaseOutput{}, fmt.Errorf("session manager not available")
		}

		// Verify database exists by listing databases
		listResp, err := ragClient.ListDatabases()
		if err != nil {
			return nil, SwitchDatabaseOutput{}, fmt.Errorf("failed to list databases: %w", err)
		}

		// Parse the response to check if database exists
		found := false
		if listResp.Data != nil {
			if dataMap, ok := listResp.Data.(map[string]any); ok {
				if databases, ok := dataMap["databases"].([]any); ok {
					for _, db := range databases {
						if dbMap, ok := db.(map[string]any); ok {
							if dbMap["name"] == input.DatabaseName {
								found = true
								break
							}
						}
					}
				}
			}
		}

		if !found {
			return nil, SwitchDatabaseOutput{}, fmt.Errorf("database '%s' not found", input.DatabaseName)
		}

		// Save to session manager
		if err := sessionManager.SetUserActiveDatabase(userID, input.DatabaseName); err != nil {
			return nil, SwitchDatabaseOutput{}, fmt.Errorf("failed to switch database: %w", err)
		}

		return nil, SwitchDatabaseOutput{
			Message:      fmt.Sprintf("Successfully switched to database '%s'", input.DatabaseName),
			DatabaseName: input.DatabaseName,
		}, nil
	}
}

func listDatabasesTool(ragClient *RAGClient) func(
	ctx context.Context,
	req *mcp.CallToolRequest,
	input ListDatabasesInput,
) (*mcp.CallToolResult, ListDatabasesOutput, error) {
	return func(
		ctx context.Context,
		req *mcp.CallToolRequest,
		input ListDatabasesInput,
	) (*mcp.CallToolResult, ListDatabasesOutput, error) {
		resp, err := ragClient.ListDatabases()
		if err != nil {
			return nil, ListDatabasesOutput{}, err
		}

		databases := []map[string]any{}
		count := 0

		if resp.Data != nil {
			if dataMap, ok := resp.Data.(map[string]any); ok {
				if dbList, ok := dataMap["databases"].([]any); ok {
					for _, db := range dbList {
						if dbMap, ok := db.(map[string]any); ok {
							databases = append(databases, dbMap)
						}
					}
				}
				if cnt, ok := dataMap["count"].(float64); ok {
					count = int(cnt)
				}
			}
		}

		return nil, ListDatabasesOutput{
			Databases: databases,
			Count:     count,
		}, nil
	}
}

// Helper functions
func getString(m map[string]any, key string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

func getFloat64(m map[string]any, key string) float64 {
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
		Host:         "0.0.0.0",   // Changed from 127.0.0.1 to bind on all interfaces
		ExternalHost: "127.0.0.1", // Default external address
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

	if extHost := os.Getenv("GO_MCP_EXTERNAL_HOST"); extHost != "" {
		config.ExternalHost = extHost
	}

	return config
}

// Define a custom type for context keys
type contextKey string

const userIDKey contextKey = "user_id"

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
	// Use external address for OAuth URLs
	externalAddr := config.ExternalHost + ":" + config.Port
	globalOAuthManager = NewSimpleOAuthManager(externalAddr)
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

	mcp.AddTool(server, &mcp.Tool{
		Name:        "switch_database",
		Description: "Switch to a different database for search operations",
	}, switchDatabaseTool(ragClient))

	mcp.AddTool(server, &mcp.Tool{
		Name:        "list_databases",
		Description: "List all available databases",
	}, listDatabasesTool(ragClient))

	// Create MCP handler
	mcpHandler := mcp.NewStreamableHTTPHandler(func(req *http.Request) *mcp.Server {
		// Extract OAuth token and add to context
		if authHeader := req.Header.Get("Authorization"); strings.HasPrefix(authHeader, "Bearer ") {
			token := strings.TrimPrefix(authHeader, "Bearer ")
			if oauthToken, exists := globalOAuthManager.tokens[token]; exists && !isTokenExpired(oauthToken) {
				// Add user_id to request context
				ctx := context.WithValue(req.Context(), userIDKey, oauthToken.UserID)
				*req = *req.WithContext(ctx)
				log.Printf("🔐 Authenticated user: %s", oauthToken.UserID)
			}
		}
		if userIDHeader := req.Header.Get("X-User-ID"); userIDHeader != "" {
			// For testing purposes, allow setting user_id via header
			ctx := context.WithValue(req.Context(), userIDKey, userIDHeader)
			*req = *req.WithContext(ctx)
			log.Printf("🔐 Test user from header: %s", userIDHeader)
		}

		return server
	}, nil)

	// Register MCP endpoint
	http.Handle("/sse", mcpHandler)

	// Add search logs endpoint (all logs or filtered by user_id)
	http.HandleFunc("/search-logs", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Get optional user_id parameter
		userID := r.URL.Query().Get("user_id")
		if userID == "" {
			userID = r.Header.Get("X-User-ID")
		}

		// Get optional limit parameter
		limitStr := r.URL.Query().Get("limit")
		limit := 0
		if limitStr != "" {
			fmt.Sscanf(limitStr, "%d", &limit)
		}

		// Get logs (userID empty = all logs)
		logs, err := sessionManager.GetSearchLogs(userID, limit)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		response := map[string]any{
			"count": len(logs),
			"logs":  logs,
		}
		if userID != "" {
			response["user_id"] = userID
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	})

	// Create logging middleware for all requests
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("📡 %s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)
		if r.URL.Path != "/sse" && r.URL.Path != "/search-logs" {
			http.NotFound(w, r)
		}
	})

	log.Printf("🚀 Starting Go MCP Server on http://%s", serverAddr)
	log.Printf("🌐 External address: http://%s", externalAddr)
	log.Printf("🐍 Python RAG Service URL: %s", config.PythonRAGURL)
	log.Printf("📋 Available tools: initialize_rag, search_documents, get_system_status, session_management, switch_database, list_databases")
	log.Printf("🔗 MCP endpoint: http://%s/sse", externalAddr)
	log.Printf("💡 For Claude Code: claude mcd add -t http go-mcp http://%s/sse", externalAddr)
	log.Printf("📊 Session Management: SQLite database (./sessions.db)")
	log.Printf("🗄️  Multi-database support: Users can switch between different vector databases")
	log.Printf("🔐 OAuth 2.1 endpoints (MCP-compliant):")
	log.Printf("   GET  /.well-known/oauth-authorization-server - OAuth Discovery metadata")
	log.Printf("   GET  /.well-known/oauth-protected-resource - Protected Resource metadata")
	log.Printf("   GET  /oauth/authorize - Authorization endpoint")
	log.Printf("   POST /oauth/token - Token endpoint")
	log.Printf("   POST /register - Dynamic client registration")
	log.Printf("📋 Search logs endpoint:")
	log.Printf("   GET  /search-logs - Get all search logs")
	log.Printf("   GET  /search-logs?user_id=<user>&limit=<n> - Get user search logs")

	// Start the HTTP server
	if err := http.ListenAndServe(serverAddr, nil); err != nil {
		log.Fatal("Server failed:", err)
	}
}
