"""Command-line interface for Flipper MCP server."""

import asyncio
import sys


def main() -> None:
    """
    Main CLI entry point.
    
    Runs the Flipper MCP server.
    """
    print("Starting Flipper Zero MCP Server...")
    
    try:
        from flipper_mcp.core.server import main as server_main
        asyncio.run(server_main())
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
