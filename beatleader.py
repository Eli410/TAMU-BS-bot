import aiohttp
import asyncio

base_url = "https://api.beatleader.xyz/"

class BeatLeaderClient:
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
            if response.status == 404:
                # Consume body so the connection can be reused
                await response.read()
                return None
            response.raise_for_status()
            return await response.json()

    async def get_player_by_discord_id(self, discord_id: str):
        return await self._request(f"player/discord/{discord_id}")

if __name__ == "__main__":
    async def main():
        async with BeatLeaderClient() as client:
            player = await client.get_player_by_discord_id("38562716725962335")
            if not player:
                print("Player not found.")
            else:
                print(f"Player found: {player['name']}")

    asyncio.run(main())