from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from types import ModuleType
from typing import Iterable

import discord
from discord.ext import commands
from Commands._helpers import update_command_mentions

from beatsaver import BeatSaverClient
from beatleader import BeatLeaderClient

log = logging.getLogger(__name__)


def _discover_module_names(package: str, directory: Path) -> list[str]:
    if not directory.exists():
        log.warning("%s directory %s does not exist", package, directory.resolve())
        return []

    module_names: list[str] = []
    for module_path in sorted(directory.glob("*.py")):
        if module_path.name.startswith("_"):
            continue
        module_names.append(f"{package}.{module_path.stem}")

    return module_names


def _import_modules(module_names: Iterable[str]) -> list[ModuleType]:
    modules: list[ModuleType] = []
    for name in module_names:
        modules.append(importlib.import_module(name))
    return modules


COMMAND_MODULE_NAMES = _discover_module_names("Commands", Path("Commands"))
EVENT_MODULE_NAMES = _discover_module_names("Events", Path("Events"))

COMMAND_MODULES = _import_modules(COMMAND_MODULE_NAMES)
EVENT_MODULES = _import_modules(EVENT_MODULE_NAMES)


class DiscordClient(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        self.start_time: int = 0
        self.beatsaver = BeatSaverClient()
        self.beatleader = BeatLeaderClient()

    async def setup_hook(self) -> None:
        self.start_time = int(discord.utils.utcnow().timestamp())
        await self._register_modules(COMMAND_MODULES, "command")
        await self._register_modules(EVENT_MODULES, "event")
        synced = await self.tree.sync()
        update_command_mentions(synced)
        log.info("Synced %s application commands", len(synced))

    async def _register_modules(self, modules: Iterable[ModuleType], label: str) -> None:
        for module in modules:
            setup_callable = getattr(module, "setup", None)
            if setup_callable is None:
                log.debug("Module %s does not expose setup(), skipping", module.__name__)
                continue

            if inspect.iscoroutinefunction(setup_callable):
                await setup_callable(self)
            else:
                setup_callable(self)
            log.info("Registered %s module %s", label, module.__name__)
