"""Check MongoDB server version."""

import asyncio
from pymongo import AsyncMongoClient
from mdrag.settings import load_settings


async def main():
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)

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
