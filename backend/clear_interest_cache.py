#!/usr/bin/env python3
"""
Script to clear the interest cache in Supabase.
Run this after updating the interest resolver logic to force re-resolution.
"""
import asyncio
from app.db.supabase_client import clear_interest_cache


async def main():
    print("Clearing interest cache...")
    deleted_count = await clear_interest_cache()
    print(f"✓ Cleared {deleted_count} cached interests")
    print("All interests will now re-resolve with the new audience size filter.")


if __name__ == "__main__":
    asyncio.run(main())
