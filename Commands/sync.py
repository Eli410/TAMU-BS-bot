from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from ._helpers import update_command_mentions


description = """
Synchronise application commands globally or to a single guild.
"""


@app_commands.command(name="sync", description=description)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(guild_id="Guild ID to sync commands to; leave empty to sync globally")
async def sync_commands(
    interaction: discord.Interaction,
    guild_id: Optional[int] = None,
) -> None:
    tree = interaction.client.tree

    await interaction.response.defer(ephemeral=True, thinking=True)

    scope_message = "globally"
    try:
        if guild_id is not None:
            guild = discord.Object(id=guild_id)
            synced = await tree.sync(guild=guild)
            scope_message = f"to guild {guild_id}"
        else:
            synced = await tree.sync()
        update_command_mentions(synced)
    except discord.HTTPException as exc:
        await interaction.followup.send(
            f"Failed to sync commands {scope_message}: {exc}", ephemeral=True
        )
        return

    await interaction.followup.send(
        f"Synced {len(synced)} commands {scope_message}.", ephemeral=True
    )


def setup(bot: discord.Client) -> None:
    bot.tree.add_command(sync_commands)
