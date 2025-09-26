# SimpleRAG Makefile
# Cross-platform build automation for Go MCP server

# Variables
BINARY_NAME=simplerag-mcp
GO_FILES=server/main.go server/session_manager.go server/oauth.go
SERVER_DIR=server
BUILD_DIR=build
VERSION?=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS=-ldflags "-X main.Version=$(VERSION)"

# Default target
.PHONY: all
all: build

# Build for current platform
.PHONY: build
build:
	@echo "Building $(BINARY_NAME) for current platform (pure Go)..."
	cd $(SERVER_DIR) && CGO_ENABLED=0 go build $(LDFLAGS) -o ../$(BINARY_NAME) .

# Build for Windows
.PHONY: build-windows
build-windows:
	@echo "Building $(BINARY_NAME) for Windows (pure Go)..."
	@mkdir -p $(BUILD_DIR)
	cd $(SERVER_DIR) && CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o ../$(BUILD_DIR)/$(BINARY_NAME)-windows-amd64.exe .

# Build for Linux
.PHONY: build-linux
build-linux:
	@echo "Building $(BINARY_NAME) for Linux (pure Go)..."
	@mkdir -p $(BUILD_DIR)
	cd $(SERVER_DIR) && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o ../$(BUILD_DIR)/$(BINARY_NAME)-linux-amd64 .

# Build for macOS
.PHONY: build-macos
build-macos:
	@echo "Building $(BINARY_NAME) for macOS (pure Go)..."
	@mkdir -p $(BUILD_DIR)
	cd $(SERVER_DIR) && CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o ../$(BUILD_DIR)/$(BINARY_NAME)-macos-amd64 .
	cd $(SERVER_DIR) && CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o ../$(BUILD_DIR)/$(BINARY_NAME)-macos-arm64 .

# Build for all platforms
.PHONY: build-all
build-all: build-windows build-linux build-macos
	@echo "Built binaries for all platforms in $(BUILD_DIR)/"

# Install dependencies
.PHONY: deps
deps:
	@echo "Installing Go dependencies..."
	go mod download
	go mod tidy

# Run tests
.PHONY: test
test:
	@echo "Running tests..."
	go test -v ./...

# Run with race detection
.PHONY: test-race
test-race:
	@echo "Running tests with race detection..."
	go test -race -v ./...

# Format code
.PHONY: fmt
fmt:
	@echo "Formatting Go code..."
	go fmt ./...

# Lint code
.PHONY: lint
lint:
	@echo "Linting Go code..."
	golangci-lint run

# Vet code
.PHONY: vet
vet:
	@echo "Vetting Go code..."
	go vet ./...

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(BINARY_NAME)
	rm -f $(BINARY_NAME).exe
	rm -rf $(BUILD_DIR)

# Run the Go MCP server
.PHONY: run
run: build
	@echo "Starting Go MCP Server with OAuth authentication..."
	./$(BINARY_NAME)

# Run Go MCP server with custom config
.PHONY: run-config
run-config: build
	@echo "Starting Go MCP Server with custom configuration..."
	PYTHON_RAG_URL=http://127.0.0.1:8008 GO_MCP_HOST=127.0.0.1 GO_MCP_PORT=8009 ./$(BINARY_NAME)

# Development setup
.PHONY: dev-setup
dev-setup: deps
	@echo "Setting up development environment..."
	@if ! command -v golangci-lint >/dev/null 2>&1; then \
		echo "Installing golangci-lint..."; \
		go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest; \
	fi

# Check everything (format, vet, lint, test)
.PHONY: check
check: fmt vet lint test
	@echo "All checks passed!"

# Release build (optimized)
.PHONY: release
release:
	@echo "Building release version..."
	@mkdir -p $(BUILD_DIR)
	cd $(SERVER_DIR) && CGO_ENABLED=0 go build $(LDFLAGS) -o ../$(BUILD_DIR)/$(BINARY_NAME) -trimpath -a .
	@echo "Release binary created: $(BUILD_DIR)/$(BINARY_NAME)"

# Docker build
.PHONY: docker-build
docker-build:
	@echo "Building Docker image..."
	docker build -t simplerag-mcp:$(VERSION) .

# Start development servers
.PHONY: dev-start
dev-start:
	@echo "Starting development servers..."
	@echo "Starting Python RAG server..."
	@python rag_http_server.py --host 127.0.0.1 --port 8008 &
	@sleep 3
	@echo "Starting Go MCP server with OAuth..."
	@$(MAKE) run

# Start only Go MCP server (assumes Python RAG is already running)
.PHONY: mcp-start
mcp-start: build
	@echo "Starting Go MCP Server with OAuth authentication..."
	@echo "Endpoints will be available at:"
	@echo "  MCP: http://127.0.0.1:8009/sse"
	@echo "  OAuth Discovery: http://127.0.0.1:8009/.well-known/oauth-authorization-server"
	@echo "  OAuth Login: http://127.0.0.1:8009/oauth/authorize"
	./$(BINARY_NAME)

# Stop development servers
.PHONY: dev-stop
dev-stop:
	@echo "Stopping development servers..."
	@pkill -f "rag_http_server.py" || true
	@pkill -f "$(BINARY_NAME)" || true

# Show build info
.PHONY: info
info:
	@echo "Build Information:"
	@echo "  Binary name: $(BINARY_NAME)"
	@echo "  Version: $(VERSION)"
	@echo "  Go version: $(shell go version)"
	@echo "  Build files: $(GO_FILES)"

# Help
.PHONY: help
help:
	@echo "SimpleRAG Makefile Commands:"
	@echo ""
	@echo "Build Commands:"
	@echo "  build          - Build for current platform"
	@echo "  build-windows  - Build for Windows x64"
	@echo "  build-linux    - Build for Linux x64"
	@echo "  build-macos    - Build for macOS (x64 and ARM64)"
	@echo "  build-all      - Build for all platforms"
	@echo "  release        - Optimized release build"
	@echo ""
	@echo "Development Commands:"
	@echo "  dev-setup      - Setup development environment"
	@echo "  dev-start      - Start both Python RAG and Go MCP servers"
	@echo "  dev-stop       - Stop development servers"
	@echo "  mcp-start      - Start only Go MCP server with OAuth"
	@echo "  run            - Build and run Go MCP server"
	@echo "  run-config     - Run Go MCP server with custom config"
	@echo ""
	@echo "Quality Commands:"
	@echo "  test           - Run tests"
	@echo "  test-race      - Run tests with race detection"
	@echo "  fmt            - Format code"
	@echo "  lint           - Lint code"
	@echo "  vet            - Vet code"
	@echo "  check          - Run all quality checks"
	@echo ""
	@echo "Utility Commands:"
	@echo "  deps           - Install dependencies"
	@echo "  clean          - Clean build artifacts"
	@echo "  info           - Show build information"
	@echo "  docker-build   - Build Docker image"
	@echo "  help           - Show this help"