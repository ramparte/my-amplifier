#!/usr/bin/env python3
"""
CLI for M365 Agent Collaboration.

Usage:
    python -m m365_collaboration.cli <operation> [options]
    
Examples:
    python -m m365_collaboration.cli post_task --title "Review code" --description "Check auth module"
    python -m m365_collaboration.cli get_pending_tasks
    python -m m365_collaboration.cli claim_task --task-id msg-xxxxx
"""

import argparse
import json
import os
import sys

# Add parent to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m365_collaboration.collaboration import AgentCollaboration


def main():
    parser = argparse.ArgumentParser(description="M365 Agent Collaboration CLI")
    parser.add_argument("operation", help="Operation to perform")
    parser.add_argument("--title", help="Message/task title")
    parser.add_argument("--content", "--description", dest="content", help="Message content or task description")
    parser.add_argument("--status-text", help="Status update text")
    parser.add_argument("--task-id", help="Task ID for claim/complete operations")
    parser.add_argument("--priority", choices=["high", "normal", "low"], default="normal")
    parser.add_argument("--context", help="JSON context data")
    parser.add_argument("--result", help="JSON result data for complete_task")
    parser.add_argument("--limit", type=int, default=20, help="Max messages to return")
    parser.add_argument("--type", dest="message_type", help="Filter by message type")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--agent-id", help="Override agent ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Get credentials from environment
    tenant_id = os.environ.get("M365_TENANT_ID")
    client_id = os.environ.get("M365_CLIENT_ID")
    client_secret = os.environ.get("M365_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        print("Error: M365 credentials required", file=sys.stderr)
        print("Set: M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET", file=sys.stderr)
        sys.exit(1)

    collab = AgentCollaboration(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        agent_id=args.agent_id or f"amplifier-cli-{os.getpid()}",
    )

    try:
        result = None
        
        if args.operation == "post_task":
            if not args.title:
                print("Error: --title required for post_task", file=sys.stderr)
                sys.exit(1)
            context = json.loads(args.context) if args.context else None
            msg = collab.post_task(
                title=args.title,
                description=args.content or "",
                priority=args.priority,
                context=context,
            )
            result = {"success": True, "task": msg.to_dict()}

        elif args.operation == "post_status":
            if not args.title:
                print("Error: --title required for post_status", file=sys.stderr)
                sys.exit(1)
            msg = collab.post_status(
                title=args.title,
                status_text=args.status_text or args.content or "",
                task_id=args.task_id,
            )
            result = {"success": True, "status": msg.to_dict()}

        elif args.operation == "post_message":
            if not args.title:
                print("Error: --title required for post_message", file=sys.stderr)
                sys.exit(1)
            context = json.loads(args.context) if args.context else None
            msg = collab.post_message(
                title=args.title,
                content=args.content or "",
                priority=args.priority,
                context=context,
            )
            result = {"success": True, "message": msg.to_dict()}

        elif args.operation == "post_handoff":
            if not args.title or not args.context:
                print("Error: --title and --context required for post_handoff", file=sys.stderr)
                sys.exit(1)
            context = json.loads(args.context)
            msg = collab.post_handoff(
                title=args.title,
                description=args.content or "",
                context=context,
            )
            result = {"success": True, "handoff": msg.to_dict()}

        elif args.operation == "get_messages":
            messages = collab.get_messages(
                message_type=args.message_type,
                status=args.status,
                limit=args.limit,
            )
            result = {"success": True, "messages": [m.to_dict() for m in messages], "count": len(messages)}

        elif args.operation == "get_pending_tasks":
            tasks = collab.get_pending_tasks()
            result = {"success": True, "tasks": [t.to_dict() for t in tasks], "count": len(tasks)}

        elif args.operation == "claim_task":
            if not args.task_id:
                print("Error: --task-id required for claim_task", file=sys.stderr)
                sys.exit(1)
            msg = collab.claim_task(args.task_id)
            if msg:
                result = {"success": True, "task": msg.to_dict()}
            else:
                result = {"success": False, "error": "Task not found"}

        elif args.operation == "complete_task":
            if not args.task_id:
                print("Error: --task-id required for complete_task", file=sys.stderr)
                sys.exit(1)
            task_result = json.loads(args.result) if args.result else None
            msg = collab.complete_task(args.task_id, task_result)
            if msg:
                result = {"success": True, "task": msg.to_dict()}
            else:
                result = {"success": False, "error": "Task not found"}

        else:
            result = {"success": False, "error": f"Unknown operation: {args.operation}"}

        # Output
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                if "task" in result:
                    t = result["task"]
                    print(f"✓ Task: {t['title']} (id: {t['id']}, status: {t['status']})")
                elif "tasks" in result:
                    print(f"Found {result['count']} pending tasks:")
                    for t in result["tasks"]:
                        print(f"  - [{t['priority']}] {t['title']} (id: {t['id']})")
                        print(f"    {t['content'][:100]}..." if len(t['content']) > 100 else f"    {t['content']}")
                elif "messages" in result:
                    print(f"Found {result['count']} messages:")
                    for m in result["messages"]:
                        print(f"  [{m['message_type']}] {m['title']} ({m['status']})")
                elif "status" in result:
                    s = result["status"]
                    print(f"✓ Status posted: {s['title']} (id: {s['id']})")
                elif "message" in result:
                    m = result["message"]
                    print(f"✓ Message posted: {m['title']} (id: {m['id']})")
                elif "handoff" in result:
                    h = result["handoff"]
                    print(f"✓ Handoff posted: {h['title']} (id: {h['id']})")
            else:
                print(f"✗ Error: {result.get('error')}", file=sys.stderr)
                sys.exit(1)

    finally:
        collab.close()


if __name__ == "__main__":
    main()
