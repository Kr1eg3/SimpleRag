package main

import (
	"database/sql"
	"fmt"
	"log"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

// SimpleSessionManager manages user chunk IDs for deduplication
type SimpleSessionManager struct {
	db    *sql.DB
	mutex sync.RWMutex
}

// NewSimpleSessionManager creates a new session manager with SQLite database
func NewSimpleSessionManager(dbPath string) (*SimpleSessionManager, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	sm := &SimpleSessionManager{
		db: db,
	}

	// Create tables
	if err := sm.initTables(); err != nil {
		return nil, fmt.Errorf("failed to initialize tables: %w", err)
	}

	log.Printf("📊 SQLite session manager initialized: %s", dbPath)
	return sm, nil
}

// initTables creates the necessary database tables
func (sm *SimpleSessionManager) initTables() error {
	query := `
	CREATE TABLE IF NOT EXISTS user_chunks (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		user_id TEXT NOT NULL,
		chunk_id TEXT NOT NULL,
		timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
	);

	CREATE INDEX IF NOT EXISTS idx_user_chunks_user_id ON user_chunks(user_id);
	CREATE INDEX IF NOT EXISTS idx_user_chunks_chunk_id ON user_chunks(chunk_id);
	CREATE UNIQUE INDEX IF NOT EXISTS idx_user_chunks_unique ON user_chunks(user_id, chunk_id);
	`

	_, err := sm.db.Exec(query)
	return err
}

// SaveChunkIDs saves chunk IDs for a user (for deduplication)
func (sm *SimpleSessionManager) SaveChunkIDs(userID string, chunkIDs []string) error {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	for _, chunkID := range chunkIDs {
		// Insert or ignore if already exists
		insertQuery := `INSERT OR IGNORE INTO user_chunks (user_id, chunk_id, timestamp) VALUES (?, ?, ?)`
		_, err := sm.db.Exec(insertQuery, userID, chunkID, time.Now())
		if err != nil {
			return fmt.Errorf("failed to save chunk ID %s: %w", chunkID, err)
		}
	}

	log.Printf("💾 Saved %d chunk IDs for user %s", len(chunkIDs), userID)
	return nil
}

// GetUserChunkIDs returns all chunk IDs that user has seen
func (sm *SimpleSessionManager) GetUserChunkIDs(userID string) ([]string, error) {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()

	query := `SELECT chunk_id FROM user_chunks WHERE user_id = ?`
	rows, err := sm.db.Query(query, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to query user chunk IDs: %w", err)
	}
	defer rows.Close()

	var chunkIDs []string
	for rows.Next() {
		var chunkID string
		if err := rows.Scan(&chunkID); err != nil {
			continue
		}
		chunkIDs = append(chunkIDs, chunkID)
	}

	return chunkIDs, nil
}

// ClearUserHistory removes all chunk IDs for a user
func (sm *SimpleSessionManager) ClearUserHistory(userID string) error {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	query := `DELETE FROM user_chunks WHERE user_id = ?`
	result, err := sm.db.Exec(query, userID)
	if err != nil {
		return fmt.Errorf("failed to clear history: %w", err)
	}

	rowsAffected, _ := result.RowsAffected()
	log.Printf("🗑️ Cleared %d chunk IDs for user %s", rowsAffected, userID)
	return nil
}

// GetStats returns simple statistics
func (sm *SimpleSessionManager) GetStats() (map[string]int, error) {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()

	stats := make(map[string]int)

	// Count unique users
	var totalUsers int
	err := sm.db.QueryRow(`SELECT COUNT(DISTINCT user_id) FROM user_chunks`).Scan(&totalUsers)
	if err != nil {
		return nil, fmt.Errorf("failed to count users: %w", err)
	}
	stats["total_users"] = totalUsers

	// Count total chunks
	var totalChunks int
	err = sm.db.QueryRow(`SELECT COUNT(*) FROM user_chunks`).Scan(&totalChunks)
	if err != nil {
		return nil, fmt.Errorf("failed to count chunks: %w", err)
	}
	stats["total_chunks"] = totalChunks

	return stats, nil
}

// FilterNewChunks filters out chunk IDs that user has already seen
func (sm *SimpleSessionManager) FilterNewChunks(userID string, chunkIDs []string) ([]string, error) {
	if userID == "" {
		return chunkIDs, nil // No filtering if no user ID
	}

	seenChunkIDs, err := sm.GetUserChunkIDs(userID)
	if err != nil {
		return chunkIDs, err // Return all if error getting seen chunks
	}

	// Create a set of seen chunk IDs
	seenSet := make(map[string]bool)
	for _, id := range seenChunkIDs {
		seenSet[id] = true
	}

	// Filter out seen chunks
	var newChunks []string
	for _, id := range chunkIDs {
		if !seenSet[id] {
			newChunks = append(newChunks, id)
		}
	}

	log.Printf("🔍 Filtered %d chunks -> %d new chunks for user %s", len(chunkIDs), len(newChunks), userID)
	return newChunks, nil
}

// Close closes the database connection
func (sm *SimpleSessionManager) Close() error {
	return sm.db.Close()
}