import httpx
from typing import List, Dict, Optional
import asyncio

from app.config import get_settings
from app.db.supabase_client import get_cached_interest, cache_interest


class InterestResolver:
    """Resolves interest names to Meta interest IDs using the Targeting Search API."""

    BASE_URL = "https://graph.facebook.com/v25.0"

    def __init__(self):
        settings = get_settings()
        self.access_token = settings.meta_system_token

    async def resolve_interests(
        self,
        interest_names: List[str]
    ) -> List[Dict[str, str]]:
        """
        Resolve a list of interest names to Meta interest IDs.

        Args:
            interest_names: List of interest names from Claude

        Returns:
            List of dicts with 'id' and 'name' for each resolved interest
        """
        resolved = []

        for name in interest_names:
            result = await self.resolve_single_interest(name)
            if result:
                resolved.append(result)

        return resolved

    async def resolve_single_interest(
        self,
        interest_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Resolve a single interest name to a Meta interest ID.

        First checks cache, then queries Meta API if not cached.

        Args:
            interest_name: Interest name to resolve

        Returns:
            Dict with 'id' and 'name', or None if not found
        """
        # Check cache first
        cached = await get_cached_interest(interest_name)
        if cached:
            return {
                "id": cached["interest_id"],
                "name": cached["interest_name"]
            }

        # Query Meta Targeting Search API
        result = await self._search_interest(interest_name)
        if result:
            # Cache the result


            await cache_interest(
                interest_name=interest_name,
                interest_id=result["id"],
                audience_size=result.get("audience_size")
            )
         
            return {"id": result["id"], "name": result["name"]}

        return None


    def _best_interest_match(self, query: str, results: List[Dict]) -> Optional[Dict]:
        """
        Find the best matching interest from search results.

        Priority:
        1. Filter by minimum audience size (100k+)
        2. Exact name match
        3. Query contained in result
        4. Result contained in query
        """

        if not results:
            return None

        query_lower = query.lower().strip()

        MIN_AUDIENCE_SIZE = 100_000

        qualified = [
            r for r in results
            if r.get("audience_size_lower_bound", 0) >= MIN_AUDIENCE_SIZE
        ]

        search_pool = qualified if qualified else results

        # Exact match
        for result in search_pool:
            if result["name"].lower() == query_lower:
                return result

        # Query contained in result
        for result in search_pool:
            if query_lower in result["name"].lower():
                return result

        # Result contained in query
        for result in search_pool:
            if result["name"].lower() in query_lower:
                return result

        # No safe match
        return None


   
    async def _search_interest(
        self,
        query: str
    ) -> Optional[Dict]:
        """
        Search for an interest using the Meta Targeting Search API.

        Args:
            query: Interest name to search for

        Returns:
            Best matching interest with id, name, and audience_size
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "type": "adinterest",
            "q": query,
            "access_token": self.access_token
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("data"):
                    return None

                interests = data["data"]
                best_match = self._best_interest_match(query, interests)

                if best_match:
                    return {
                        "id": best_match["id"],
                        "name": best_match["name"],
                        "audience_size": best_match.get("audience_size_lower_bound")
                    }

                return None

            except httpx.HTTPStatusError as e:
                print(f"Error searching interest '{query}': {e}")
                return None
            except Exception as e:
                print(f"Unexpected error searching interest '{query}': {e}")
                return None

    async def resolve_interests_parallel(
        self,
        interest_names: List[str],
        max_concurrent: int = 5
    ) -> List[Dict[str, str]]:
        """
        Resolve multiple interests in parallel with rate limiting.

        Args:
            interest_names: List of interest names
            max_concurrent: Maximum concurrent requests

        Returns:
            List of resolved interests
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def resolve_with_semaphore(name: str):
            async with semaphore:
                return await self.resolve_single_interest(name)

        tasks = [resolve_with_semaphore(name) for name in interest_names]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]
