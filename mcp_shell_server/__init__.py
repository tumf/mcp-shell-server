"""MCP Shell Server Package."""

import asyncio

from . import server


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ["main", "server"]
__version__ = "0.1.0"
