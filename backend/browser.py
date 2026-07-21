import os
from pathlib import Path

from agents.mcp import MCPServerStdio, create_static_tool_filter


READ_ONLY_BROWSER_TOOLS = [
    "browser_navigate",
    "browser_snapshot",
    "browser_wait_for",
    "browser_tabs",
    "browser_close",
]


class PlaywrightBrowser:
    def __init__(self, root_dir: Path, enabled: bool = True):
        self.root_dir = root_dir
        self.enabled = enabled

    async def connect(self) -> MCPServerStdio | None:
        if not self.enabled:
            return None
        binary_name = "playwright-mcp.cmd" if os.name == "nt" else "playwright-mcp"
        command = self.root_dir / "frontend" / "node_modules" / ".bin" / binary_name
        if not command.exists():
            raise RuntimeError("Playwright MCP is not installed. Run npm install in frontend.")

        output_dir = self.root_dir / "artifacts" / "browser"
        output_dir.mkdir(parents=True, exist_ok=True)
        server = MCPServerStdio(
            name="playwright",
            params={
                "command": str(command),
                "args": [
                    "--headless",
                    "--isolated",
                    "--image-responses",
                    "omit",
                    "--output-dir",
                    str(output_dir),
                ],
                "cwd": self.root_dir,
            },
            cache_tools_list=True,
            client_session_timeout_seconds=60,
            tool_filter=create_static_tool_filter(
                allowed_tool_names=READ_ONLY_BROWSER_TOOLS
            ),
        )
        try:
            await server.connect()
        except Exception:
            await server.cleanup()
            raise
        return server

    async def close(self, server: MCPServerStdio | None = None) -> None:
        if not server:
            return
        await server.cleanup()
