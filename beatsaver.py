import aiohttp
import asyncio

base_url = "https://api.beatsaver.com/"

class BeatSaverClient:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, *_):
        if self._owns_session:
            await self.close()

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=base_url)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, path: str, **kwargs):
        await self._ensure_session()
        async with self._session.get(path, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def get_maps_by_ids(self, map_ids: list[str]):
        if not map_ids:
            raise ValueError("map_ids must contain at least one id.")
        if len(map_ids) > 50:
            raise ValueError("map_ids cannot exceed 50 entries.")
        joined_ids = ",".join(map_ids)
        return await self._request(f"maps/ids/{joined_ids}")

    async def get_map_by_hash(self, hash: str):
        if not hash:
            raise ValueError("hash must be a non-empty string.")
        return await self._request(f"maps/hash/{hash}")
    
if __name__ == "__main__":
    async def main():
        async with BeatSaverClient() as client:
            maps = await client.get_maps_by_ids(["4aee1", "B2C3"])

    asyncio.run(main())