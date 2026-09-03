"""Connect to Alpaca's official MCP server over stdio."""

import argparse
import asyncio
import json
import os
import shutil
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from alphabeater.config import Settings


def alpaca_mcp_transport(settings: Settings, *, toolsets: str) -> StdioTransport:
    api_key, secret_key = settings.require_alpaca_credentials()
    uvx = shutil.which("uvx")
    if uvx is None:
        raise ValueError("uvx is required; install uv from https://docs.astral.sh/uv/")
    inherited = {
        name: value
        for name in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA")
        if (value := os.environ.get(name)) is not None
    }
    return StdioTransport(
        command=uvx,
        args=["alpaca-mcp-server"],
        env={
            **inherited,
            "ALPACA_API_KEY": api_key,
            "ALPACA_SECRET_KEY": secret_key,
            "ALPACA_PAPER_TRADE": "true",
            "ALPACA_TOOLSETS": toolsets,
        },
    )


async def inspect_mcp(*, describe: bool = False) -> dict[str, Any]:
    settings = Settings()
    async with Client(
        alpaca_mcp_transport(settings, toolsets="account,trading"), timeout=30
    ) as client:
        tools = await client.list_tools()
        result: dict[str, Any] = {
            "server": "alpaca-mcp-server",
            "paper": True,
            "tool_count": len(tools),
            "tools": [tool.name for tool in tools],
        }
        if describe:
            result["schemas"] = {
                tool.name: tool.inputSchema
                for tool in tools
                if tool.name
                in {
                    "get_account_info",
                    "get_account",
                    "get_clock",
                    "create_order",
                    "place_order",
                    "place_option_order",
                    "get_order_by_client_id",
                }
            }
        account_tool = next(
            (tool.name for tool in tools if tool.name in {"get_account_info", "get_account"}),
            None,
        )
        if account_tool is not None:
            account = await client.call_tool(account_tool, {})
            result["account_tool"] = account_tool
            result["account_result"] = account.data
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Alpaca's official MCP server")
    parser.add_argument("--describe", action="store_true", help="show selected tool schemas")
    args = parser.parse_args()
    try:
        result = asyncio.run(inspect_mcp(describe=args.describe))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Alpaca MCP check failed: {exc}")
        return 1
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
