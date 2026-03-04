import discord
from discord import app_commands
import json
from datetime import datetime
from ._helpers import _command_mentions

class TournamentsFile:
    FILE_PATH = "tournaments.json"

    @staticmethod
    def _load() -> list[dict]:
        try:
            with open(TournamentsFile.FILE_PATH, "r", encoding="utf-8") as file:
                data = file.read().strip()
                if not data:
                    return []
                return json.loads(data)
        except (FileNotFoundError, json.JSONDecodeError):
            with open(TournamentsFile.FILE_PATH, "w", encoding="utf-8") as file:
                json.dump([], file)
            return []

    @staticmethod
    def _write(tournaments: list[dict]) -> None:
        with open(TournamentsFile.FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(tournaments, file, indent=4)
    
    @staticmethod
    def get_tournaments(active: bool = True) -> list[dict]:
        tournaments = TournamentsFile._load()
        if not active:
            return tournaments

        now = datetime.now().timestamp()
        active_tournaments: list[dict] = []
        for tournament in tournaments:
            try:
                start = float(tournament.get("startDate", 0))
                end = float(tournament.get("endDate", 0))
            except (TypeError, ValueError):
                continue
            if start <= now <= end:
                active_tournaments.append(tournament)
        return active_tournaments

    @staticmethod
    def get_tournament(name: str) -> dict:
        tournaments = TournamentsFile._load()
        for tournament in tournaments:
            if tournament.get("name") == name:
                return tournament
        raise ValueError(f"Tournament '{name}' not found.")

    @staticmethod
    def save_tournament(
        name: str,
        maps: dict[str, dict[str, str]] | None = None,
        players: dict[dict[str, str]] | None = None,
    ) -> None:
        tournaments = TournamentsFile._load()
        for index, existing in enumerate(tournaments):
            if existing.get("name") == name:
                updated = existing.copy()
                if maps is not None:
                    updated["maps"] = maps
                if players is not None:
                    updated["players"] = players
                tournaments[index] = updated
                break
        else:
            tournaments.append(
                {
                    "name": name,
                    "maps": maps or {},
                    "players": players or {},
                }
            )
        TournamentsFile._write(tournaments)


class TournamentCreateModal(discord.ui.Modal, title='Create Tournament'):
    def __init__(self, name=None, maps=None) -> None:
        super().__init__()
        self.name = discord.ui.TextInput(
            label='Tournament Name', 
            placeholder='Enter the name of the tournament', 
            max_length=100, 
            default=name or ''
        )
        self.add_item(self.name)
        self.maps = maps or {}
    
    async def on_submit(self, interaction: discord.Interaction):
        TournamentsFile.save_tournament(
            name=self.name.value,
            maps=self.maps,
        )
        await interaction.response.send_message("Changes saved successfully", ephemeral=True)

class MapSelect(discord.ui.Select):
    def __init__(self, maps: dict[str, dict] | None = None) -> None:
        self.maps = maps or {}

        options: list[discord.SelectOption] = []

        if self.maps:
            # ALL option at the top; user must explicitly choose it
            options.append(
                discord.SelectOption(
                    label="ALL",
                    value="ALL",
                    description="Include all maps from the playlist",
                )
            )

            for level_id, info in self.maps.items():
                if not level_id:
                    continue
                name = info.get("name") or "Unknown Song"
                difficulty = info.get("difficulty")
                label = name
                if difficulty:
                    label = f"{name} ({difficulty})"

                options.append(
                    discord.SelectOption(
                        label=label[:100],
                        value=level_id,
                    )
                )

        max_values = max(1, min(len(options), 25))

        super().__init__(
            placeholder="Select maps for the tournament",
            min_values=1,
            max_values=max_values,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.maps:
            await interaction.response.send_message(
                "There are no maps available to create a tournament.", ephemeral=True
            )
            return

        selected_values = set(self.values)

        if "ALL" in selected_values:
            selected_maps = self.maps
        else:
            # Preserve the original playlist order by iterating over
            # the maps in their existing order and picking only the
            # ones the user selected.
            selected_maps: dict[str, dict] = {}
            for level_id, map_info in self.maps.items():
                if level_id in selected_values and map_info is not None:
                    selected_maps[level_id] = map_info

        if not selected_maps:
            await interaction.response.send_message(
                "No valid maps were selected for the tournament.", ephemeral=True
            )
            return

        modal = TournamentCreateModal(maps=selected_maps)
        await interaction.response.send_modal(modal)


class TournamentView(discord.ui.View):
    def __init__(self, timeout: float | None = None, interaction: discord.Interaction | None = None, maps=None) -> None:
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.maps = maps or {}

        if self.maps:
            self.add_item(MapSelect(self.maps))

description = """
Parse a playlist and display its contents.
"""

@app_commands.command(name="parse_playlist", description=description)
async def parse_playlist_command(interaction: discord.Interaction, file: discord.Attachment) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)

    playlist_data = await file.read()
    playlist_json = json.loads(playlist_data)
    embed = discord.Embed()
    embed.title = playlist_json.get("playlistTitle", "Playlist")
    embed.description = f"**By {playlist_json.get("playlistAuthor", "Unknown Author")}**"
    embed.color = discord.Color.blurple()
    maps = {}
    for song in playlist_json.get("songs", []):
        song_name = song.get("songName", "Unknown Song")
        song_author = song.get("levelAuthorName", "Unknown Author")
        difficulty = song.get("difficulties", "Unknown Difficulty")[0]
        hash = song.get("hash", "Unknown hash")
        map_id = await interaction.client.beatsaver.get_map_by_hash(hash)
        level_id = map_id.get("id", "Unknown ID") if map_id else ""
        song_url = f"https://beatsaver.com/maps/{level_id}" if level_id else "https://beatsaver.com/"
        embed.add_field(name=f'{song_name}', 
                        value=f"Author: {song_author}\nDifficulty: {difficulty['name']}\n[Link]({song_url})", 
                        inline=True)
        maps[level_id] = {
            "name": song_name,
            "author": song_author,
            "characteristic": difficulty['characteristic'],
            "difficulty": difficulty['name'],
            "hash": hash,
        }
    view = TournamentView(maps=maps)

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(parse_playlist_command)
