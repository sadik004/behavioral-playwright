# Model Context Protocol (MCP) Bridge Guide

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Using Behavioral Playwright as an MCP Tool Server

Expose web scraping, crawling, and search tools directly to AI agent platforms (such as Claude Desktop or custom agents) using the Model Context Protocol:

```python
import asyncio
from bp_facade12 import BP

async def handle_mcp_call():
    async with BP() as bp:
        # 1. Generate standard MCP tools manifest
        manifest = bp.integrations.generate_mcp_manifest()
        print("MCP Manifest Tools:", [t["name"] for t in manifest["tools"]])

        # 2. Execute an incoming tool call from an AI agent
        result = await bp.integrations.mcp_call_tool_async(
            tool_name="scrape",
            arguments={"url": "https://example.com"}
        )
        print("MCP Execution Result:\n", result)

if __name__ == "__main__":
    asyncio.run(handle_mcp_call())
```
