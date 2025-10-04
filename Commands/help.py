from __future__ import annotations

import discord
from discord import app_commands

from ._helpers import format_command_mentions


description = """
Show a list of the bot's registered slash commands.
"""


@app_commands.command(name="help", description=description)
async def help_command(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Help",
        description="",
        colour=discord.Color.blurple(),
    )
    embed.add_field(
        name="Registered Commands",
        value=format_command_mentions(interaction.client),
        inline=False,
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot: discord.Client) -> None:
    bot.tree.add_command(help_command)
