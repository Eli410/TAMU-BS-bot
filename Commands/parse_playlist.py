import discord
from discord import app_commands
import json

description = """
Parse a playlist and display its contents.
"""

@app_commands.command(name="parse_playlist", description=description)
async def parse_playlist_command(interaction: discord.Interaction, file: discord.Attachment) -> None:
    # read the file as json

    playlist_data = await file.read()
    playlist_json = json.loads(playlist_data)
    # create an embed to display the playlist contents
    embed = discord.Embed(title=playlist_json.get("playlistTitle", "Playlist"), description=playlist_json.get("playlistAuthor", "Unknown Author"), color=discord.Color.blue())
    

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(parse_playlist_command)
