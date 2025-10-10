import datetime as dt

import discord
from discord import app_commands



class StatusView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary)
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button["StatusView"],
    ) -> None:
        await interaction.response.edit_message(embed=new_embed(interaction.client))


def new_embed(client: discord.Client) -> discord.Embed:
    now = discord.utils.utcnow()
    color = discord.Color.blurple()

    embed = discord.Embed(title="Status", colour=color, timestamp=now)

    user = client.user
    if user is not None:
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)

    latency_ms = client.latency * 1000 if client.latency is not None else 0.0
    start_timestamp = getattr(client, "start_time", int(now.timestamp()))
    online_since = dt.datetime.fromtimestamp(start_timestamp, tz=dt.timezone.utc)

    embed.add_field(name="Latency", value=f"{latency_ms:.1f} ms", inline=False)
    embed.add_field(
        name="Online Since",
        value=discord.utils.format_dt(online_since, style="R"),
        inline=False,
    )

    return embed


description = """
Returns the bot's current status.
"""


@app_commands.command(name="status", description=description)
async def status(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        embed=new_embed(interaction.client), view=StatusView(), ephemeral=True
    )


def setup(bot: discord.Client) -> None:
    bot.tree.add_command(status)
