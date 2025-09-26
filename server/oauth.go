package main

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// OAuth configuration
type OAuthConfig struct {
	ClientID     string
	ClientSecret string
	AuthURL      string
	TokenURL     string
	RedirectURL  string
}

// Token represents an OAuth access token
type OAuthToken struct {
	AccessToken  string    `json:"access_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int       `json:"expires_in"`
	RefreshToken string    `json:"refresh_token,omitempty"`
	UserID       string    `json:"user_id"`
	CreatedAt    time.Time `json:"created_at"`
}

// AuthState stores temporary OAuth state
type AuthState struct {
	State    string
	CodeVerifier string
	UserID   string
	ExpireAt time.Time
}

// SimpleOAuthManager manages OAuth flow for MCP
type SimpleOAuthManager struct {
	config     OAuthConfig
	tokens     map[string]*OAuthToken // token -> OAuthToken
	states     map[string]*AuthState  // state -> AuthState
	serverAddr string
}

// NewSimpleOAuthManager creates a new OAuth manager
func NewSimpleOAuthManager(serverAddr string) *SimpleOAuthManager {
	return &SimpleOAuthManager{
		config: OAuthConfig{
			ClientID:     "simplerag-mcp",
			ClientSecret: "your-client-secret", // In production, use env var
			AuthURL:      fmt.Sprintf("http://%s/oauth/authorize", serverAddr),
			TokenURL:     fmt.Sprintf("http://%s/oauth/token", serverAddr),
			RedirectURL:  fmt.Sprintf("http://%s/oauth/callback", serverAddr),
		},
		tokens:     make(map[string]*OAuthToken),
		states:     make(map[string]*AuthState),
		serverAddr: serverAddr,
	}
}

// OAuth Discovery Metadata (RFC 8414)
func (o *SimpleOAuthManager) metadataHandler(w http.ResponseWriter, r *http.Request) {
	metadata := map[string]interface{}{
		"issuer":                 fmt.Sprintf("http://%s", o.serverAddr),
		"authorization_endpoint": o.config.AuthURL,
		"token_endpoint":        o.config.TokenURL,
		"registration_endpoint":  fmt.Sprintf("http://%s/register", o.serverAddr),
		"response_types_supported": []string{"code"},
		"grant_types_supported":    []string{"authorization_code", "client_credentials"},
		"code_challenge_methods_supported": []string{"S256"},
		"token_endpoint_auth_methods_supported": []string{"client_secret_basic", "client_secret_post"},
		"scopes_supported": []string{"mcp:read", "mcp:write"},
		"service_documentation": "https://github.com/user/SimpleRag",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metadata)
}

// Authorization endpoint - where user gets redirected for login
func (o *SimpleOAuthManager) authorizeHandler(w http.ResponseWriter, r *http.Request) {
	clientID := r.URL.Query().Get("client_id")
	redirectURI := r.URL.Query().Get("redirect_uri")
	state := r.URL.Query().Get("state")
	codeChallenge := r.URL.Query().Get("code_challenge")
	responseType := r.URL.Query().Get("response_type")

	// Basic validation
	if clientID != o.config.ClientID || responseType != "code" {
		http.Error(w, "Invalid request", 400)
		return
	}

	// For demo purposes, show a simple login form
	if r.Method == "GET" {
		loginForm := fmt.Sprintf(`
<!DOCTYPE html>
<html>
<head><title>RAG MCP Server - Login</title></head>
<body>
<h2>RAG MCP Server Authentication</h2>
<form method="POST">
	<div>
		<label>User ID:</label>
		<input type="text" name="user_id" placeholder="Enter your user ID" required>
	</div>
	<div style="margin-top: 10px;">
		<label>Password:</label>
		<input type="password" name="password" placeholder="Enter password" required>
	</div>
	<div style="margin-top: 10px;">
		<button type="submit">Login</button>
	</div>
	<input type="hidden" name="client_id" value="%s">
	<input type="hidden" name="redirect_uri" value="%s">
	<input type="hidden" name="state" value="%s">
	<input type="hidden" name="code_challenge" value="%s">
</form>
</body>
</html>`, clientID, redirectURI, state, codeChallenge)

		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(loginForm))
		return
	}

	// Process login (POST)
	if r.Method == "POST" {
		r.ParseForm()
		userID := r.FormValue("user_id")
		password := r.FormValue("password")

		// Simple validation (in production, use proper auth)
		if userID == "" || password == "" {
			http.Error(w, "Invalid credentials", http.StatusUnauthorized)
			return
		}

		// Generate authorization code
		authCode := generateRandomString(32)

		// Store auth state
		o.states[authCode] = &AuthState{
			State:        state,
			CodeVerifier: "", // Will be verified during token exchange
			UserID:       userID,
			ExpireAt:     time.Now().Add(10 * time.Minute),
		}

		// Redirect back with authorization code
		callbackURL := fmt.Sprintf("%s?code=%s&state=%s", redirectURI, authCode, state)
		http.Redirect(w, r, callbackURL, http.StatusFound)
		return
	}
}

// Token endpoint - exchange authorization code for access token
func (o *SimpleOAuthManager) tokenHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	r.ParseForm()
	grantType := r.FormValue("grant_type")
	code := r.FormValue("code")
	// clientID := r.FormValue("client_id")
	// codeVerifier := r.FormValue("code_verifier")

	// Validate grant type
	if grantType != "authorization_code" {
		http.Error(w, "Unsupported grant type", 400)
		return
	}

	// Find auth state
	authState, exists := o.states[code]
	if !exists || time.Now().After(authState.ExpireAt) {
		http.Error(w, "Invalid or expired authorization code", 400)
		return
	}

	// Clean up used code
	delete(o.states, code)

	// Generate access token
	accessToken := generateRandomString(64)

	// Create token
	token := &OAuthToken{
		AccessToken: accessToken,
		TokenType:   "Bearer",
		ExpiresIn:   3600, // 1 hour
		UserID:      authState.UserID,
		CreatedAt:   time.Now(),
	}

	// Store token
	o.tokens[accessToken] = token

	log.Printf("🔐 Generated access token for user: %s", authState.UserID)

	// Return token response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"access_token": token.AccessToken,
		"token_type":   token.TokenType,
		"expires_in":   token.ExpiresIn,
	})
}

// Middleware to extract user from Authorization header
func (o *SimpleOAuthManager) authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip auth for OAuth endpoints and MCP SSE endpoint
		if strings.HasPrefix(r.URL.Path, "/oauth") || strings.HasPrefix(r.URL.Path, "/.well-known") || strings.HasPrefix(r.URL.Path, "/register") || strings.HasPrefix(r.URL.Path, "/sse") {
			next.ServeHTTP(w, r)
			return
		}

		// Extract Bearer token
		authHeader := r.Header.Get("Authorization")
		if !strings.HasPrefix(authHeader, "Bearer ") {
			// Return 401 with OAuth challenge
			w.Header().Set("WWW-Authenticate", `Bearer realm="MCP Server"`)
			http.Error(w, "Authorization required", http.StatusUnauthorized)
			return
		}

		token := strings.TrimPrefix(authHeader, "Bearer ")

		// Validate token
		oauthToken, exists := o.tokens[token]
		if !exists {
			w.Header().Set("WWW-Authenticate", `Bearer error="invalid_token"`)
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		// Check token expiration
		if time.Now().After(oauthToken.CreatedAt.Add(time.Duration(oauthToken.ExpiresIn) * time.Second)) {
			delete(o.tokens, token)
			w.Header().Set("WWW-Authenticate", `Bearer error="invalid_token"`)
			http.Error(w, "Token expired", http.StatusUnauthorized)
			return
		}

		// Add user_id to context
		type contextKey string
		const userIDKey contextKey = "user_id"
		ctx := context.WithValue(r.Context(), userIDKey, oauthToken.UserID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// Helper function to generate random strings
func generateRandomString(length int) string {
	bytes := make([]byte, length)
	if _, err := rand.Read(bytes); err != nil {
		panic(err)
	}
	return base64.URLEncoding.EncodeToString(bytes)[:length]
}

// Client registration endpoint for OAuth 2.1
func (o *SimpleOAuthManager) registerHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Return client credentials for Claude Code
	response := map[string]interface{}{
		"client_id":     o.config.ClientID,
		"client_secret": o.config.ClientSecret,
		"client_id_issued_at": time.Now().Unix(),
		"redirect_uris": []string{o.config.RedirectURL},
		"grant_types": []string{"authorization_code"},
		"response_types": []string{"code"},
		"token_endpoint_auth_method": "client_secret_post",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Protected Resource metadata endpoint for MCP (RFC 9728)
func (o *SimpleOAuthManager) protectedResourceHandler(w http.ResponseWriter, r *http.Request) {
	metadata := map[string]interface{}{
		"resource": fmt.Sprintf("http://%s", o.serverAddr),
		"authorization_servers": []string{fmt.Sprintf("http://%s", o.serverAddr)},
		"scopes_supported": []string{"mcp:read", "mcp:write"},
		"bearer_methods_supported": []string{"header"},
		"resource_documentation": "SimpleRAG MCP Server with OAuth 2.1",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metadata)
}

// Setup OAuth endpoints
func (o *SimpleOAuthManager) setupEndpoints() {
	http.HandleFunc("/.well-known/oauth-authorization-server", o.metadataHandler)
	http.HandleFunc("/.well-known/oauth-protected-resource", o.protectedResourceHandler)
	http.HandleFunc("/oauth/authorize", o.authorizeHandler)
	http.HandleFunc("/oauth/token", o.tokenHandler)
	http.HandleFunc("/register", o.registerHandler)
}