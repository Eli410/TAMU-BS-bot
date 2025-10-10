import discord
from discord import app_commands
import json
from datetime import datetime
from zoneinfo import ZoneInfo

def _discord_timestamp(value: int | float | str | None, style: str = "F") -> str:
    try:
        return f"<t:{int(value)}:{style}>"
    except (TypeError, ValueError):
        return "Unknown"


async def build_tournaments_embed(interaction: discord.Interaction, tournaments: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="Scheduled tournaments overview" if len(tournaments) > 1 else "Tournament details",
        description="",
        colour=discord.Color.blurple(),
    )
    if not tournaments:
        embed.description = "No tournaments registered."
        return embed

    for tournament in tournaments:
        isRegistered = any(str(interaction.user.id) == player.get('discordId') for player in tournament.get('players', []))
        start_ts = _discord_timestamp(tournament.get("startDate"), "R")
        end_ts = _discord_timestamp(tournament.get("endDate"), "R")
        
        numMaps = len(tournament.get("mapIds", []))
        
        numPlayers = len(tournament.get("players", []))
        

        field_value = (
            f"**Start:** {start_ts}\n"
            f"**End:** {end_ts}\n"
            f"**{numMaps}** maps\n"
            f"**{numPlayers}** players registered"
        )
        embed.add_field(
            name=f'{tournament.get("name", "Untitled Tournament")} {'✅' if isRegistered else '❌'}',
            value=field_value,
            inline=True,
        )

    return embed

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
        maps: list[str] | None = None,
        players: list[dict] | None = None,
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
                    updated["mapIds"] = maps
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
                    "mapIds": maps or [],
                    "players": players or [],
                }
            )
        TournamentsFile._write(tournaments)
    
class ConfirmationModal(discord.ui.Modal, title='Confirmation'):
    def __init__(self, message: str, action) -> None:
        super().__init__()
        self.message = discord.ui.TextInput(
            label='Type "CONFIRM" to proceed', 
            placeholder=message, 
            max_length=20
        )
        self.add_item(self.message)
        self.action = action
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.message.value.strip().upper() == "CONFIRM":
            await self.action(interaction)
        else:
            await interaction.response.send_message("Action cancelled. Confirmation text did not match.", ephemeral=True)

class TournamentCreateModal(discord.ui.Modal, title='Create Tournament'):
    def __init__(self, name=None, startTime=None, endTime=None) -> None:
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
        )
        await interaction.response.send_message(f"Changes saved successfully", ephemeral=True)

class TournamentEditModal(TournamentCreateModal, title='Edit Tournament'):
    def __init__(self, name, startTime, endTime) -> None:
        super().__init__(name, startTime, endTime)


class TournamentView(discord.ui.View):
    def __init__(self, *, timeout: float | None = None) -> None:
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Select Tournament", style=discord.ButtonStyle.green)
    async def select(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = discord.ui.View()
        view.add_item(TournamentPicker(TournamentsFile.get_tournaments(active=False), interaction))
        await interaction.response.send_message("Select a tournament to view:", view=view, ephemeral=True)

class TournamentPicker(discord.ui.Select):
    def __init__(self, tournaments: list[dict], interaction: discord.Interaction) -> None:
        options = [
            discord.SelectOption(
                label=tournament.get("name", "Untitled Tournament"),
                description=f"Starts: {_discord_timestamp(tournament.get('startDate'))}, Ends: {_discord_timestamp(tournament.get('endDate'))}",
                value=tournament.get("name", "Untitled Tournament"),
            )
            for tournament in tournaments
        ]
        self.interaction = interaction
        super().__init__(placeholder="Select a tournament...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_tournament_name = self.values[0]
        tournament = TournamentsFile.get_tournament(selected_tournament_name)
        embed = await build_tournaments_embed(interaction, [tournament])
        admin_role_id = 849470981751177267
        has_admin_role = (
            isinstance(interaction.user, discord.Member)
            and any(role.id == admin_role_id for role in interaction.user.roles)
        )

        await interaction.response.defer()
        if has_admin_role:
            view = TournamentAdminDetailView(tournament, interaction)
            await self.interaction.edit_original_response(embed=embed, view=view)
            return
        view = TournamentDetailView(tournament, interaction)
        await self.interaction.edit_original_response(embed=embed, view=view)

class TournamentDetailView(discord.ui.View):
    def __init__(self, tournament: dict, interaction: discord.Interaction) -> None:
        super().__init__(timeout=None)
        self.tournament = tournament
        self.interaction = interaction
        self.update_buttons()
        
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join_tournament(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        discord_id = str(interaction.user.id)
        player = await interaction.client.beatleader.get_player_by_discord_id(discord_id)
        if not player:
            await interaction.response.send_message("Discord not linked in beatleader, go [link it](https://beatleader.com/signin/socials)", ephemeral=True)
            return
        
        TournamentsFile.save_tournament(
            name=self.tournament.get("name", ""),
            players=self.tournament.get("players", []) + [{"discordId": discord_id, "beatleaderUsername": player["name"]}],
        )
        embed = await build_tournaments_embed(interaction.client, [TournamentsFile.get_tournament(self.tournament.get("name", ""))])
        self.tournament = TournamentsFile.get_tournament(self.tournament.get("name", ""))
        self.update_buttons()
        await interaction.response.defer()
        await self.interaction.edit_original_response(content=f"You have joined the tournament '{self.tournament.get('name', '')}'.", embed=embed, view=self)

    @discord.ui.button(label="Withdraw", style=discord.ButtonStyle.red)
    async def withdraw_tournament(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        async def action(interaction: discord.Interaction) -> None:
            discord_id = str(interaction.user.id)
            updated_players = [
                player for player in self.tournament.get("players", [])
                if player.get("discordId") != discord_id
            ]
            TournamentsFile.save_tournament(
                name=self.tournament.get("name", ""),
                players=updated_players
            )
            embed = await build_tournaments_embed(interaction, [TournamentsFile.get_tournament(self.tournament.get("name", ""))])
            self.tournament = TournamentsFile.get_tournament(self.tournament.get("name", ""))
            self.update_buttons()
            await interaction.response.defer()
            await interaction.edit_original_response(content=f"You have withdrawn from the tournament '{self.tournament.get('name', '')}'.", embed=embed, view=self)
        
        modal = ConfirmationModal(
            message=f'Are you sure you want to withdraw from the tournament "{self.tournament.get("name", "")}"?',
            action=action
        )
        await interaction.response.send_modal(modal)

    def update_buttons(self) -> None:
        discord_id = str(self.interaction.user.id)
        is_registered = any(
            player.get("discordId") == discord_id
            for player in self.tournament.get("players", [])
        )
        self.join_tournament.disabled = is_registered
        self.withdraw_tournament.disabled = not is_registered

class TournamentAdminDetailView(TournamentDetailView):
    def __init__(self, tournament: dict, interaction: discord.Interaction) -> None:
        super().__init__(tournament, interaction)

    @discord.ui.button(label="Edit Tournament", style=discord.ButtonStyle.primary)
    async def edit_tournament(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        start_time = datetime.fromtimestamp(self.tournament["startDate"]).strftime('%Y-%m-%d %H:%M')
        end_time = datetime.fromtimestamp(self.tournament["endDate"]).strftime('%Y-%m-%d %H:%M')
        modal = TournamentEditModal(
            name=self.tournament.get("name", ""),
            startTime=start_time,
            endTime=end_time,
        )
        await interaction.response.send_modal(modal)

class TournamentAdminView(TournamentView):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Create event", style=discord.ButtonStyle.primary)
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = TournamentCreateModal()
        await interaction.response.send_modal(modal)


description = "Create, manage, and view tournaments."
@app_commands.command(name="tournaments", description=description)
async def tournaments(interaction: discord.Interaction) -> None:
    tournament_ = TournamentsFile.get_tournaments(active=False)
    embed = await build_tournaments_embed(interaction, tournament_)
    view = TournamentAdminView() if interaction.user.guild_permissions.administrator else TournamentView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(tournaments)
