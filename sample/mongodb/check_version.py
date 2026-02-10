"""Check MongoDB server version."""

import asyncio

from mdrag.config.settings import load_settings
from pymongo import AsyncMongoClient


async def main():
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_connection_string, serverSelectionTimeoutMS=5000)

    try:
        info = await client.admin.command("buildInfo")
        print("MongoDB Version:", info.get("version"))
        print("Git Version:", info.get("gitVersion"))
        print("Modules:", info.get("modules"))
    except Exception as e:
        print(f"Error retrieving version info: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
