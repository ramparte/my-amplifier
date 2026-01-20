#!/usr/bin/env python3
"""Quick test of M365 collaboration connectivity."""

import os
import sys

# Add to path for local import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collaboration import AgentCollaboration


def test():
    tenant_id = os.environ.get("M365_TENANT_ID")
    client_id = os.environ.get("M365_CLIENT_ID")
    client_secret = os.environ.get("M365_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing credentials. Set M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET")
        return False

    print("Testing M365 collaboration...")
    
    try:
        collab = AgentCollaboration(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            agent_id="test-agent",
        )
        
        # Test getting messages
        messages = collab.get_messages(limit=5)
        print(f"✅ Connected! Found {len(messages)} recent messages.")
        
        for msg in messages[:3]:
            print(f"   [{msg.message_type}] {msg.title}")
        
        collab.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test()
    sys.exit(0 if success else 1)
