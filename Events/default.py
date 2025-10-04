from __future__ import annotations

import discord
from discord.ext import commands


async def setup(bot: commands.Bot) -> None:
    @bot.event
    async def on_message(message: discord.Message) -> None:
        return None
