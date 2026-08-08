"""MCP Shell Server Package."""

from . import server
from .version import __version__

__all__ = ["__version__", "main", "server"]


def main():
    """Main entry point for the package."""
    import asyncio

    asyncio.run(server.main())


if __name__ == "__main__":
    main()
