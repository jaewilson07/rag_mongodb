"""Check MongoDB cluster information and capabilities."""

import asyncio

from mdrag.config.settings import load_settings
from pymongo import AsyncMongoClient


async def main():
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_connection_string, serverSelectionTimeoutMS=5000)

    try:
        info = await client.admin.command("buildInfo")
        print("MongoDB Version:", info.get("version"))
        print("Storage Engines:", info.get("storageEngines", []))
        print("Max BSON Size:", info.get("maxBsonObjectSize"))
        print("Bits:", info.get("bits"))
        print("Debug:", info.get("debug"))
        print("OpenSSL:", info.get("openssl"))

        # Check server status
        status = await client.admin.command("serverStatus")
        print("\nCluster Status:")
        print("Uptime:", status.get("uptime"))
        print("Connections:", status.get("connections"))
        print("Memory:", status.get("mem"))

    except Exception as e:
        print(f"Error retrieving cluster info: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
