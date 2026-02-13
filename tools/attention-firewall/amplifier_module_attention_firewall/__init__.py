"""Amplifier tool for querying Attention Firewall notification database."""

from amplifier_core import ToolResult
from .tool import AttentionFirewallTool

__all__ = ["AttentionFirewallTool", "mount"]


async def mount(coordinator, config=None):
    """Mount the attention firewall tool."""
    config = config or {}
    tool = AttentionFirewallTool()
    await coordinator.mount("tools", tool, name=tool.name)
    return None
