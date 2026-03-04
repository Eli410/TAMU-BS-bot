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

    async def search_players(self, search: str, count: int = 5):
        """
        Search players by BeatLeader username using the /players endpoint.

        Returns the list of matching players (may be empty).
        """
        if not search:
            return []
        data = await self._request(
            "players",
            params={
                "search": search,
                "count": count,
            },
        )
        if not isinstance(data, dict):
            return []
        players = data.get("data")
        if isinstance(players, list):
            return players
        return []

    async def get_single_player_by_name(self, search: str):
        """
        Resolve a single player by BeatLeader username.

        Returns:
        - player dict when at least one match is found (first result)
        - None when no players are found
        """
        players = await self.search_players(search, count=5)
        if not players:
            return None
        return players[0]

    async def get_player_score(self, player: dict, map: dict):
        """Return only the raw score value for backwards compatibility."""
        score = await self.get_player_score_with_accuracy(player, map)
        if score is None:
            return None
        return score.get("score")

    async def get_player_score_with_accuracy(self, player: dict, map: dict):
        """
        Return a dict containing both raw score and BeatLeader accuracy (percentage).

        The returned structure is:
        {
            "score": int | None,
            "accuracy": float | None,  # 0-100 (percentage)
        }
        """
        id = player.get("beatleaderId")
        hash = map.get("hash")
        difficulty = map.get("difficulty")
        characteristic = map.get("characteristic")

        # This endpoint returns the score value for the given map/difficulty.
        # It does not include accuracy, so we derive percentage elsewhere.
        data = await self._request(
            f"player/{id}/scorevalue/{hash}/{difficulty}/{characteristic}"
        )
        if data is None:
            return None

        # scorevalue returns a raw numeric score
        raw_score = data if isinstance(data, (int, float)) else None

        return {
            "score": raw_score,
            "accuracy": None,
        }

if __name__ == "__main__":
    async def main():
        async with BeatLeaderClient() as client:
            player = await client.get_player_by_discord_id("38562716725962335")
            if not player:
                print("Player not found.")
            else:
                print(f"Player found: {player['name']}")

    asyncio.run(main())