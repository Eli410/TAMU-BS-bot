import discord
from discord import app_commands


description = """
Get information about your BeatLeader account.
"""

@app_commands.command(name="me", description=description)
async def me_command(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)

    user = await interaction.client.beatleader.get_player_by_discord_id(
        str(interaction.user.id)
    )

    if not user:
        await interaction.followup.send(
            "You don't have Discord linked in your BeatLeader, link it [here](https://beatleader.com/signin/socials).", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"{user.get('name', 'Unknown')} (#{user.get('rank', 'N/A')})",
        url=f"https://beatleader.xyz/u/{user.get('id', '')}",
        color=discord.Color.blurple(),
    )
    embed.set_thumbnail(url=user.get("avatar", ""))

    pp = user.get("pp", 0)
    play_count = user.get("playCount", 0)
    hours_played = user.get("hoursPlayed", 0.0)
    country_rank = user.get("countryRank", 0)

    embed.add_field(name=f"{''.join(chr(ord(char.upper()) + 127397) for char in user.get('country'))} Rank", value=f"#{country_rank}", inline=True)
    embed.add_field(name="PP", value=f"{pp:.2f}", inline=True)
    if user.get("clans"):
        embed.add_field(name="Clan", value=user.get("clans")[0].get('tag'), inline=True)

    await interaction.followup.send(embed=embed, ephemeral=True)

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(me_command)