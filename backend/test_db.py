import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load explicitly here just in case
load_dotenv(dotenv_path="../.env")

from db.database import init_db, close_db
from db.models import Base

logging.basicConfig(level=logging.INFO)

async def test():
    try:
        print("Initializing database...")
        await init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(test())
