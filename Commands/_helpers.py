from __future__ import annotations

from typing import Iterable

import discord
from discord import app_commands


_command_mentions: list[str] = []


def update_command_mentions(commands: Iterable[app_commands.AppCommand]) -> None:
    global _command_mentions

    mentions: list[str] = []
    for command in commands:
        command_id = getattr(command, "id", None)
        if command_id is None:
            mentions.append(f"`/{command.name}` (unsynced)")
        else:
            mentions.append(f"</{command.name}:{command_id}>")

    _command_mentions = mentions


def format_command_mentions(_: discord.Client | None = None) -> str:
    if not _command_mentions:
        return "No commands registered."
    return "\n".join(_command_mentions)

def get_command_mentions(name) -> str:
    for command in _command_mentions:
        if f'/{name}:' in command or f'`/{name}`' in command:
            return command
    return f"`/{name}` (unsynced)"