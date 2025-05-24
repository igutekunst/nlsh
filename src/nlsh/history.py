"""Command and interaction history management using SQLite"""

import sqlite3
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path

from .shell import CommandResult


@dataclass
class HistoryEntry:
    """Base class for history entries"""
    id: Optional[int]
    timestamp: datetime
    session_id: str
    entry_type: str  # 'shell_command', 'llm_interaction', 'context_snapshot'
    cwd: str


@dataclass  
class ShellCommandEntry(HistoryEntry):
    """History entry for shell commands"""
    command: str
    output: str
    error: str
    return_code: int
    execution_time_ms: Optional[int] = None


@dataclass
class LLMInteractionEntry(HistoryEntry):
    """History entry for LLM interactions"""
    user_prompt: str
    generated_commands: List[str]
    executed_commands: List[str]
    execution_results: List[Dict[str, Any]]  # List of CommandResult dicts
    llm_model: str
    context_snapshot: Optional[str] = None


class HistoryManager:
    """Manages command and interaction history in SQLite"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to user's home directory
            home_dir = Path.home()
            nlsh_dir = home_dir / '.nlsh'
            nlsh_dir.mkdir(exist_ok=True)
            db_path = nlsh_dir / 'history.db'
            
        self.db_path = str(db_path)
        self.session_id = self._generate_session_id()
        self._init_database()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(os.getpid())
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    cwd TEXT NOT NULL,
                    data TEXT NOT NULL  -- JSON data specific to entry type
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON history_entries(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON history_entries(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_type ON history_entries(entry_type)")
            
            conn.commit()
    
    def log_shell_command(self, command: str, result: CommandResult, execution_time_ms: int = None):
        """Log a shell command execution"""
        entry = ShellCommandEntry(
            id=None,
            timestamp=datetime.now(),
            session_id=self.session_id,
            entry_type='shell_command',
            cwd=result.cwd,
            command=command,
            output=result.output,
            error=result.error,
            return_code=result.return_code,
            execution_time_ms=execution_time_ms
        )
        
        self._save_entry(entry)
    
    def log_llm_interaction(self, user_prompt: str, generated_commands: List[str], 
                          executed_commands: List[str], execution_results: List[CommandResult],
                          llm_model: str = "unknown", context_snapshot: str = None):
        """Log an LLM interaction"""
        # Convert CommandResult objects to dicts for JSON serialization
        result_dicts = [asdict(result) for result in execution_results]
        
        entry = LLMInteractionEntry(
            id=None,
            timestamp=datetime.now(),
            session_id=self.session_id,
            entry_type='llm_interaction',
            cwd=os.getcwd(),
            user_prompt=user_prompt,
            generated_commands=generated_commands,
            executed_commands=executed_commands,
            execution_results=result_dicts,
            llm_model=llm_model,
            context_snapshot=context_snapshot
        )
        
        self._save_entry(entry)
    
    def log_context_snapshot(self, context_data: Dict[str, Any]):
        """Log a context snapshot"""
        entry = HistoryEntry(
            id=None,
            timestamp=datetime.now(),
            session_id=self.session_id,
            entry_type='context_snapshot',
            cwd=os.getcwd()
        )
        
        # Store context data as JSON
        self._save_entry(entry, extra_data=context_data)
    
    def _save_entry(self, entry: HistoryEntry, extra_data: Dict[str, Any] = None):
        """Save a history entry to the database"""
        with sqlite3.connect(self.db_path) as conn:
            # Prepare data for JSON serialization
            if extra_data:
                data = extra_data
            else:
                data = asdict(entry)
                # Remove fields that are stored separately
                data.pop('id', None)
                data.pop('timestamp', None)
                data.pop('session_id', None)
                data.pop('entry_type', None)
                data.pop('cwd', None)
            
            conn.execute("""
                INSERT INTO history_entries (timestamp, session_id, entry_type, cwd, data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                entry.timestamp.isoformat(),
                entry.session_id,
                entry.entry_type,
                entry.cwd,
                json.dumps(data, default=str)  # default=str handles datetime objects
            ))
            
            conn.commit()
    
    def get_session_history(self, session_id: str = None) -> List[Dict[str, Any]]:
        """Get history for a specific session"""
        if session_id is None:
            session_id = self.session_id
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            
            cursor = conn.execute("""
                SELECT * FROM history_entries 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,))
            
            entries = []
            for row in cursor.fetchall():
                entry = dict(row)
                entry['data'] = json.loads(entry['data'])
                entries.append(entry)
                
            return entries
    
    def get_recent_commands(self, limit: int = 10, entry_type: str = None) -> List[Dict[str, Any]]:
        """Get recent commands/interactions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM history_entries"
            params = []
            
            if entry_type:
                query += " WHERE entry_type = ?"
                params.append(entry_type)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entry = dict(row)
                entry['data'] = json.loads(entry['data'])
                entries.append(entry)
                
            return entries
    
    def search_history(self, search_term: str, entry_type: str = None) -> List[Dict[str, Any]]:
        """Search history entries by content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT * FROM history_entries 
                WHERE data LIKE ?
            """
            params = [f'%{search_term}%']
            
            if entry_type:
                query += " AND entry_type = ?"
                params.append(entry_type)
                
            query += " ORDER BY timestamp DESC LIMIT 50"
            
            cursor = conn.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entry = dict(row)
                entry['data'] = json.loads(entry['data'])
                entries.append(entry)
                
            return entries
    
    def get_command_stats(self) -> Dict[str, Any]:
        """Get statistics about command usage"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total entries
            cursor = conn.execute("SELECT COUNT(*) FROM history_entries")
            stats['total_entries'] = cursor.fetchone()[0]
            
            # Entries by type
            cursor = conn.execute("""
                SELECT entry_type, COUNT(*) as count 
                FROM history_entries 
                GROUP BY entry_type
            """)
            stats['by_type'] = dict(cursor.fetchall())
            
            # Commands by session
            cursor = conn.execute("""
                SELECT session_id, COUNT(*) as count 
                FROM history_entries 
                GROUP BY session_id 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_sessions'] = dict(cursor.fetchall())
            
            # Recent activity (last 7 days)
            cursor = conn.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM history_entries 
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            stats['recent_activity'] = dict(cursor.fetchall())
            
            return stats
    
    def cleanup_old_entries(self, days_to_keep: int = 30):
        """Remove entries older than specified days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM history_entries 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
    
    def export_history(self, output_file: str, session_id: str = None):
        """Export history to JSON file"""
        if session_id:
            entries = self.get_session_history(session_id)
        else:
            entries = self.get_recent_commands(limit=1000)  # Export recent 1000 entries
            
        with open(output_file, 'w') as f:
            json.dump(entries, f, indent=2, default=str)
            
        return len(entries) 