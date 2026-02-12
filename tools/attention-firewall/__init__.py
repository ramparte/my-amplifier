"""Amplifier tool for querying Attention Firewall database."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class AttentionFirewallTool:
    """Query the Attention Firewall notification database."""
    
    name = "attention_firewall"
    description = """Query the Attention Firewall notification database.
    
Available queries:
- recent: Get recent important notifications (surfaced items)
- timeframe: Get notifications from a specific time period  
- suppressed: Get suppressed notifications to audit filtering rules
- stats: Get statistics about notification filtering
- all: Get all notifications in a time period
"""
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "enum": ["recent", "timeframe", "suppressed", "stats", "all"],
                "description": "Type of query to run",
            },
            "limit": {
                "type": "integer",
                "description": "Number of results (for recent queries)",
                "default": 10,
            },
            "hours": {
                "type": "number", 
                "description": "Time period in hours (for timeframe queries)",
                "default": 1.0,
            },
        },
        "required": ["query"],
    }
    
    def __init__(self):
        self.db_path = Path.home() / ".attention-firewall" / "notifications.db"
    
    async def execute(
        self,
        query: str,
        limit: int = 10,
        hours: float = 1.0,
        **kwargs: Any,
    ) -> dict:
        """Execute a query against the firewall database."""
        if not self.db_path.exists():
            return {
                "error": "Attention Firewall database not found. Is the daemon running?",
            }
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            if query == "recent":
                result = self._query_recent(conn, limit)
            elif query == "timeframe":
                result = self._query_timeframe(conn, hours)
            elif query == "suppressed":
                result = self._query_suppressed(conn, hours)
            elif query == "stats":
                result = self._query_stats(conn, hours)
            elif query == "all":
                result = self._query_all(conn, hours)
            else:
                conn.close()
                return {"error": f"Unknown query type: {query}"}
            
            conn.close()
            return result
            
        except Exception as e:
            return {"error": f"Database query failed: {e}"}
    
    def _query_recent(self, conn: sqlite3.Connection, limit: int) -> dict:
        """Get recent important (surfaced) notifications."""
        cursor = conn.cursor()
        
        notifications = cursor.execute("""
            SELECT 
                timestamp,
                app_id,
                sender,
                title,
                body,
                rationale
            FROM notifications
            WHERE action = 'SURFACE'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
        return {
            "query": "recent",
            "count": len(notifications),
            "notifications": [dict(n) for n in notifications],
        }
    
    def _query_timeframe(self, conn: sqlite3.Connection, hours: float) -> dict:
        """Get important notifications from a time period."""
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        
        notifications = cursor.execute("""
            SELECT 
                timestamp,
                app_id,
                sender,
                title,
                body,
                rationale
            FROM notifications
            WHERE action = 'SURFACE'
              AND timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff.isoformat(),)).fetchall()
        
        return {
            "query": "timeframe",
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "count": len(notifications),
            "notifications": [dict(n) for n in notifications],
        }
    
    def _query_suppressed(self, conn: sqlite3.Connection, hours: float) -> dict:
        """Get suppressed notifications to audit filtering."""
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        
        notifications = cursor.execute("""
            SELECT 
                timestamp,
                app_id,
                sender,
                title,
                body,
                rationale
            FROM notifications
            WHERE action = 'SUPPRESS'
              AND timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff.isoformat(),)).fetchall()
        
        # Group by rationale to show patterns
        by_reason: dict[str, int] = {}
        for n in notifications:
            reason = n['rationale'] or 'Unknown'
            by_reason[reason] = by_reason.get(reason, 0) + 1
        
        return {
            "query": "suppressed",
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "count": len(notifications),
            "by_reason": by_reason,
            "notifications": [dict(n) for n in notifications],
        }
    
    def _query_stats(self, conn: sqlite3.Connection, hours: float) -> dict:
        """Get statistics about notification filtering."""
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        
        stats = cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN action = 'SURFACE' THEN 1 ELSE 0 END) as surfaced,
                SUM(CASE WHEN action = 'DIGEST' THEN 1 ELSE 0 END) as digested,
                SUM(CASE WHEN action = 'SUPPRESS' THEN 1 ELSE 0 END) as suppressed
            FROM notifications
            WHERE timestamp > ?
        """, (cutoff.isoformat(),)).fetchone()
        
        # Get top apps
        top_apps = cursor.execute("""
            SELECT app_id, COUNT(*) as count
            FROM notifications
            WHERE timestamp > ?
            GROUP BY app_id
            ORDER BY count DESC
            LIMIT 5
        """, (cutoff.isoformat(),)).fetchall()
        
        return {
            "query": "stats",
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "total": stats['total'],
            "surfaced": stats['surfaced'],
            "digested": stats['digested'],
            "suppressed": stats['suppressed'],
            "surface_rate": round(stats['surfaced'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0,
            "top_apps": [dict(a) for a in top_apps],
        }
    
    def _query_all(self, conn: sqlite3.Connection, hours: float) -> dict:
        """Get ALL notifications in time period."""
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=hours)
        
        notifications = cursor.execute("""
            SELECT 
                timestamp,
                app_id,
                sender,
                title,
                body,
                action,
                rationale
            FROM notifications
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff.isoformat(),)).fetchall()
        
        # Group by action
        by_action: dict[str, int] = {}
        for n in notifications:
            action = n['action']
            by_action[action] = by_action.get(action, 0) + 1
        
        return {
            "query": "all",
            "hours": hours,
            "cutoff": cutoff.isoformat(),
            "count": len(notifications),
            "by_action": by_action,
            "notifications": [dict(n) for n in notifications],
        }
