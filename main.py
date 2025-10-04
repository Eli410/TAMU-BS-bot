import asyncio
import logging
import os

from dotenv import load_dotenv

from client import DiscordClient


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )


def get_token() -> str:
    load_dotenv()
    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("Discord bot token not found in environment variable TOKEN")
    return token


async def run_bot() -> None:
    token = get_token()
    async with DiscordClient() as bot:
        await bot.start(token)


def main() -> None:
    configure_logging()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
