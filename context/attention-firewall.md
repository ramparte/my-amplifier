# Attention Firewall Integration

You have access to the `attention_firewall` tool for querying your notification firewall database.

## What You Can Ask

**Recent important notifications:**
- "What are the last 10 things I should know about?"
- "Show me recent important notifications"
- "What did I miss?"

**Time-based queries:**
- "What happened in the last hour I should know about?"
- "Give me a 3 hour summary"
- "What's been happening in the last 2 hours?"

**Suppression audit (check filtering rules):**
- "What have you suppressed in the last 2 hours?"
- "Show me what got filtered out today"
- "What notifications did you block?"
- "Are my firewall rules working correctly?"

**Statistics:**
- "How many notifications came in today?"
- "What's my surface rate?"
- "Which apps are noisiest?"
- "Show me notification stats for the last 6 hours"

**Complete review:**
- "Show me everything from the last hour"
- "Give me all notifications from today"

**Dashboard location:**
- "Where is my firewall dashboard?"
- "Open my firewall dashboard"

## Tool Parameters

The `attention_firewall` tool accepts:

- `query`: Type of query (recent, timeframe, suppressed, stats, all)
- `limit`: Number of results for recent queries (default: 10)
- `hours`: Time period in hours for timeframe/suppressed/stats/all queries (default: 1.0)

## Dashboard

The live dashboard is at: `C:\Users\samschillace\.attention-firewall\dashboard.html`

It auto-refreshes every 30 seconds and shows:
- Last 100 important (surfaced) notifications
- 24-hour statistics
- Real-time updates when new important notifications arrive

## Database Location

The notification database is at: `C:\Users\samschillace\.attention-firewall\notifications.db`

All queries use this SQLite database which is populated by the attention-firewall daemon.
