import discord
from discord import app_commands
import json
from datetime import datetime
from zoneinfo import ZoneInfo
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
        startDate: int | float | str | None = None,
        endDate: int | float | str | None = None,
        maps: dict[str, dict[str, str]] | None = None,
        players: dict[dict[str, str]] | None = None,
    ) -> None:
        tournaments = TournamentsFile._load()
        for index, existing in enumerate(tournaments):
            if existing.get("name") == name:
                updated = existing.copy()
                if startDate is not None:
                    updated["startDate"] = startDate
                if endDate is not None:
                    updated["endDate"] = endDate
                if maps is not None:
                    updated["maps"] = maps
                if players is not None:
                    updated["players"] = players
                tournaments[index] = updated
                break
        else:
            if startDate is None or endDate is None:
                raise ValueError("startDate and endDate are required for new tournaments.")
            tournaments.append(
                {
                    "name": name,
                    "startDate": startDate,
                    "endDate": endDate,
                    "maps": maps or {},
                    "players": players or [],
                }
            )
        TournamentsFile._write(tournaments)


class TournamentCreateModal(discord.ui.Modal, title='Create Tournament'):
    def __init__(self, name=None, startTime=None, endTime=None, maps=None) -> None:
        super().__init__()
        central_now = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M")
        self.name = discord.ui.TextInput(
            label='Tournament Name', 
            placeholder='Enter the name of the tournament', 
            max_length=100, 
            default=name or ''
        )
        self.startTime = discord.ui.TextInput(
            label='Start Time (YYYY-MM-DD HH:MM)',
            placeholder='Enter the start time (e.g., YYYY-MM-DD HH:MM)',
            max_length=50,
            default=startTime or central_now,
        )
        self.endTime = discord.ui.TextInput(
            label='End Time (YYYY-MM-DD HH:MM)',
            placeholder='Enter the end time (e.g., YYYY-MM-DD HH:MM)',
            max_length=50,
            default=endTime or central_now,
        )
        self.add_item(self.name)
        self.add_item(self.startTime)
        self.add_item(self.endTime)
        self.maps = maps or {}
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            start_timestamp = int(datetime.strptime(self.startTime.value, '%Y-%m-%d %H:%M').timestamp())
            end_timestamp = int(datetime.strptime(self.endTime.value, '%Y-%m-%d %H:%M').timestamp())
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD HH:MM.", ephemeral=True)
            return
        


        TournamentsFile.save_tournament(
            name=self.name.value,
            startDate=start_timestamp,
            endDate=end_timestamp,
            maps=self.maps,
        )
        await interaction.response.send_message(f"Changes saved successfully", ephemeral=True)

class TournamentView(discord.ui.View):
    def __init__(self, timeout: float | None = None, interaction: discord.Interaction | None = None, maps=None) -> None:
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.maps = maps or {}

    @discord.ui.button(label="Create tournament", style=discord.ButtonStyle.primary)
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = TournamentCreateModal(maps=self.maps)
        await interaction.response.send_modal(modal)

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
                        value=f"Author: {song_author}\nDifficulty: {difficulty['characteristic']} - {difficulty['name']}\n[Link]({song_url})", 
                        inline=True)
        maps[level_id] = {
            "characteristic": difficulty['characteristic'],
            "difficulty": difficulty['name'],
            "hash": hash
        }
    view = TournamentView(maps=maps)

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(parse_playlist_command)
