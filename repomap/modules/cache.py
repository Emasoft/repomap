#!/usr/bin/env python3
"""
Cache management functions for RepoMap.
"""
import os
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Any, Tuple

from .config import CACHE_VERSION, SQLITE_ERRORS

class Cache:
    """Cache manager for RepoMap."""
    
    def __init__(self, io, root=None, verbose=False):
        """Initialize the cache manager."""
        self.io = io
        self.root = root or os.getcwd()
        self.verbose = verbose
        self.cache_dir = os.path.join(self.root, ".repomap.tags.cache.v4")
        self.conn = None
        self.cursor = None
        self.load_cache()
    
    def load_cache(self):
        """Load or create the SQLite cache."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            db_path = os.path.join(self.cache_dir, "cache.db")
            
            # Check if the DB is locked
            try:
                self.conn = sqlite3.connect(db_path)
                self.cursor = self.conn.cursor()
                
                # Create tables if they don't exist
                self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """)
                
                self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_tags (
                    file_path TEXT,
                    mtime FLOAT,
                    tags BLOB,
                    PRIMARY KEY (file_path)
                )
                """)
                
                # Check schema version
                self.cursor.execute("SELECT value FROM meta WHERE key = 'version'")
                row = self.cursor.fetchone()
                if row is None:
                    self.cursor.execute("INSERT INTO meta VALUES ('version', ?)", (str(CACHE_VERSION),))
                elif int(row[0]) != CACHE_VERSION:
                    # Clear cache on version mismatch
                    self.cursor.execute("DELETE FROM file_tags")
                    self.cursor.execute("UPDATE meta SET value = ? WHERE key = 'version'", (str(CACHE_VERSION),))
                
                self.conn.commit()
                
                if self.verbose:
                    self.io.tool_output("Cache initialized.")
                
            except SQLITE_ERRORS as e:
                self.cache_error(e)
        
        except Exception as e:
            self.cache_error(e)
    
    def cache_error(self, original_error=None):
        """Handle cache errors gracefully."""
        if original_error and self.verbose:
            self.io.tool_warning(f"Cache error: {original_error}")
        
        # Close any existing connection
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        
        # Reinitialize with in-memory database
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_tags (
            file_path TEXT,
            mtime FLOAT,
            tags BLOB,
            PRIMARY KEY (file_path)
        )
        """)
        
        # Set version
        self.cursor.execute("INSERT OR REPLACE INTO meta VALUES ('version', ?)", (str(CACHE_VERSION),))
        self.conn.commit()
        
        if self.verbose:
            self.io.tool_warning("Using temporary cache due to error.")
    
    def get_cached_tags(self, file_path: str, mtime: float) -> Optional[Any]:
        """Get cached tags for a file if available and not stale."""
        if not self.conn:
            return None
        
        try:
            self.cursor.execute(
                "SELECT tags FROM file_tags WHERE file_path = ? AND mtime = ?",
                (file_path, mtime)
            )
            row = self.cursor.fetchone()
            if row:
                import pickle
                return pickle.loads(row[0])
        except (SQLITE_ERRORS, pickle.UnpicklingError) as e:
            if self.verbose:
                self.io.tool_warning(f"Error retrieving from cache: {e}")
        
        return None
    
    def save_tags_to_cache(self, file_path: str, mtime: float, tags: Any) -> bool:
        """Save tags to cache."""
        if not self.conn:
            return False
        
        try:
            import pickle
            serialized_tags = pickle.dumps(tags)
            
            self.cursor.execute(
                "INSERT OR REPLACE INTO file_tags VALUES (?, ?, ?)",
                (file_path, mtime, serialized_tags)
            )
            self.conn.commit()
            return True
        
        except (SQLITE_ERRORS, pickle.PicklingError) as e:
            if self.verbose:
                self.io.tool_warning(f"Error saving to cache: {e}")
            return False
    
    def close(self):
        """Close the cache connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                self.cursor = None
            except Exception as e:
                if self.verbose:
                    self.io.tool_warning(f"Error closing cache: {e}")
                self.conn = None
                self.cursor = None
