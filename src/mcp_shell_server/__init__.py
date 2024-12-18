"""MCP Shell Server Package."""

from . import server

__version__ = "0.1.0"
__all__ = ["main", "server"]


def main():
    """Main entry point for the package."""
    import asyncio

    asyncio.run(server.main())


if __name__ == "__main__":
    main()
