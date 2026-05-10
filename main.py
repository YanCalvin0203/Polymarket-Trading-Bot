import asyncio

from src.core.settings import settings


async def main():
  settings.NODE_CONFIG.inject_to_env()


if __name__ == "__main__":
  asyncio.run(main())
