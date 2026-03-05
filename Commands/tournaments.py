import discord
from discord import app_commands
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from ._helpers import get_command_mentions
def _discord_timestamp(value: int | float | str | None, style: str = "F") -> str:
    try:
        return f"<t:{int(value)}:{style}>"
    except (TypeError, ValueError):
        return "Unknown"


def _set_leaderboard_refresh_footer(embed: discord.Embed) -> None:
    """Set the embed footer and timestamp so Discord shows 'Last refreshed' with a rendered time."""
    now = discord.utils.utcnow()
    embed.timestamp = now
    embed.set_footer(text="Last refreshed")


async def build_tournaments_embed(interaction: discord.Interaction, tournaments: list[dict]) -> discord.Embed:
    if not tournaments:
        return discord.Embed(
            title="Scheduled tournaments overview",
            description=f"No tournaments registered. Use {get_command_mentions('parse_playlist')} to create one.",
            colour=discord.Color.blurple(),
        )

    embed = discord.Embed(
        title="Scheduled tournaments overview",
        description="",
        colour=discord.Color.blurple(),
    )
    
    for tournament in tournaments:
        players = tournament.get("players", {})
        numPlayers = len(players)
        numMaps = len(tournament.get("maps", []))
        field_lines: list[str] = []

        start_raw = tournament.get("startDate")
        end_raw = tournament.get("endDate")
        if start_raw is not None:
            field_lines.append(f"**Start:** {_discord_timestamp(start_raw, 'R')}")
        if end_raw is not None:
            field_lines.append(f"**End:** {_discord_timestamp(end_raw, 'R')}")

        field_lines.append(f"**{numMaps}** maps")
        field_lines.append(f"**{numPlayers}** players registered")

        field_value = "\n".join(field_lines)
        embed.add_field(
            name=tournament.get("name", "Untitled Tournament"),
            value=field_value,
            inline=True,
        )
    return embed


async def build_tournament_detail_embed(
    interaction: discord.Interaction, tournament: dict, *, loading: bool = False
) -> discord.Embed:
    players: dict = tournament.get("players", {})

    embed = discord.Embed(
        title=tournament.get("name", "Untitled Tournament"),
        description="",
        colour=discord.Color.blurple(),
    )
    
    start_raw = tournament.get("startDate")
    end_raw = tournament.get("endDate")

    if start_raw is not None:
        embed.add_field(name="Start", value=_discord_timestamp(start_raw, "F"), inline=True)
    if end_raw is not None:
        embed.add_field(name="End", value=_discord_timestamp(end_raw, "F"), inline=False)
    
    maps_config = tournament.get("maps") or {}
    map_ids = list(maps_config.keys())
    
    data = await interaction.client.beatsaver.get_maps_by_ids(map_ids) if map_ids else {}
    # Ensure map order matches the JSON (playlist) order
    for map_id in map_ids:
        map = data.get(map_id)
        if not map:
            continue

        map_name = f'{map.get("metadata", {}).get("songName", "Unknown")}'
        map_config = (tournament.get("maps") or {}).get(map_id, {})
        characteristic = map_config.get("characteristic", "Unknown")
        difficulty = map_config.get("difficulty", "Unknown")

        if loading:
            scores_text = "Loading..."
        else:
            # Derive the max score for this map/difficulty from BeatSaver data
            versions = map.get("versions") or []
            max_score_for_map: int | None = None
            target_hash = map_config.get("hash", "").upper()
            for version in versions:
                if str(version.get("hash", "")).upper() != target_hash:
                    continue
                for diff in version.get("diffs", []):
                    if (
                        diff.get("difficulty") == difficulty
                        and diff.get("characteristic") == characteristic
                    ):
                        max_score_for_map = diff.get("maxScore")
                        break
                if max_score_for_map is not None:
                    break

            score_entries: list[tuple[str, float | int | None, float | None]] = []
            for player_data in players.values():
                try:
                    score_data = await interaction.client.beatleader.get_player_score_with_accuracy(player_data, map_config)
                except Exception:
                    score_data = None
                if score_data is None:
                    score_value = None
                    accuracy_value = None
                else:
                    score_value = score_data.get("score")
                    # If BeatLeader accuracy is not present, derive percentage from BeatSaver maxScore
                    bl_accuracy = score_data.get("accuracy")
                    if isinstance(bl_accuracy, (int, float)):
                        accuracy_value = float(bl_accuracy)
                    elif isinstance(score_value, (int, float)) and isinstance(max_score_for_map, (int, float)) and max_score_for_map > 0:
                        accuracy_value = (score_value / max_score_for_map) * 100.0
                    else:
                        accuracy_value = None
                score_entries.append((player_data["beatleaderUsername"], score_value, accuracy_value))

            score_entries.sort(key=lambda item: item[1] if item[1] is not None else float("-inf"), reverse=True)
            max_name = max((len(username) for username, _, _ in score_entries), default=0)
            max_score = max(
                (len(str(score)) if score is not None else len("N/A") for _, score, _ in score_entries),
                default=0,
            )
            max_percent = max(
                (
                    len(f"{accuracy:.2f}%")
                    if accuracy is not None
                    else len("N/A%")
                    for _, _, accuracy in score_entries
                ),
                default=0,
            )
            scores_text = (
                "\n".join(
                    f"{username.ljust(max_name)}  "
                    f"{(str(score) if score is not None else 'N/A').rjust(max_score)}  "
                    f"{(f'{accuracy:.2f}%' if accuracy is not None else 'N/A%').rjust(max_percent)}"
                    for username, score, accuracy in score_entries
                )
                if score_entries
                else "No scores recorded."
            )

        embed.add_field(
            name="",
            value=(
                f"[{map_name} {characteristic} - {difficulty}]"
                f"(https://beatsaver.com/maps/{map.get('id', '')})\n```{scores_text}```"
            ),
            inline=False,
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
        maps: dict | None = None,
        players: dict | None = None,
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
                    updated["maps"] = maps
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
                    "maps": maps or {},
                    "players": players or {},
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
    def __init__(self, *, timeout: float | None = None, interaction: discord.Interaction) -> None:
        super().__init__(timeout=timeout)
        self.interaction = interaction
        if TournamentsFile.get_tournaments(active=False):
            self.add_item(TournamentPicker(TournamentsFile.get_tournaments(active=False), interaction))

class TournamentPicker(discord.ui.Select):
    def __init__(self, tournaments: list[dict], interaction: discord.Interaction = None) -> None:
        options = []
        for tournament in tournaments:
            start_raw = tournament.get("startDate")
            end_raw = tournament.get("endDate")
            desc_parts: list[str] = []
            if start_raw is not None:
                desc_parts.append(f"Starts: {_discord_timestamp(start_raw)}")
            if end_raw is not None:
                desc_parts.append(f"Ends: {_discord_timestamp(end_raw)}")

            description = ", ".join(desc_parts) if desc_parts else "Schedule not set"

            options.append(
                discord.SelectOption(
                    label=tournament.get("name", "Untitled Tournament"),
                    description=description,
                    value=tournament.get("name", "Untitled Tournament"),
                )
            )
        self.interaction = interaction
        super().__init__(placeholder="Select a tournament...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_tournament_name = self.values[0]
        tournament = TournamentsFile.get_tournament(selected_tournament_name)
        embed = await build_tournament_detail_embed(interaction, tournament)
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
            # If Discord is not linked, ask for BeatLeader username or let the user choose to link instead.
            modal = JoinWithUsernameModal(self)
            await interaction.response.send_modal(modal)
            return
        
        updated_players = self.tournament.get("players", {})
        updated_players[discord_id] = {
            "beatleaderUsername": player["name"],
            "beatleaderId": player["id"]
        }
        
        TournamentsFile.save_tournament(
            name=self.tournament.get("name", ""),
            players=updated_players
        )

        updated_tournament = TournamentsFile.get_tournament(self.tournament.get("name", ""))
        embed = await build_tournament_detail_embed(interaction, updated_tournament)
        self.tournament = updated_tournament
        self.update_buttons()
        await interaction.response.defer()
        await self.interaction.edit_original_response(content=f"You have joined the tournament '{self.tournament.get('name', '')}'.", embed=embed, view=self)

    def update_buttons(self) -> None:
        discord_id = str(self.interaction.user.id)
        is_registered = discord_id in self.tournament.get("players", {})
        self.join_tournament.disabled = is_registered

class TournamentAdminDetailView(TournamentDetailView):
    def __init__(self, tournament: dict, interaction: discord.Interaction) -> None:
        super().__init__(tournament, interaction)

    @discord.ui.button(label="Edit Tournament", style=discord.ButtonStyle.primary)
    async def edit_tournament(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        def _format_ts(value) -> str:
            try:
                return datetime.fromtimestamp(float(value)).strftime('%Y-%m-%d %H:%M')
            except (TypeError, ValueError, OSError):
                return ""

        start_time = _format_ts(self.tournament.get("startDate"))
        end_time = _format_ts(self.tournament.get("endDate"))
        modal = TournamentEditModal(
            name=self.tournament.get("name", ""),
            startTime=start_time,
            endTime=end_time,
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Register Player", style=discord.ButtonStyle.primary)
    async def register_player(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        modal = RegisterPlayerModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove Player", style=discord.ButtonStyle.red)
    async def remove_player(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        players = self.tournament.get("players", {}) or {}
        if not players:
            await interaction.response.send_message(
                "No players are currently registered for this tournament.", ephemeral=True
            )
            return

        view = RemovePlayerView(self.tournament, self.interaction)
        # Keep the current embed; just swap the view to the removal view.
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Post leaderboard", style=discord.ButtonStyle.secondary)
    async def post_leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.channel or not isinstance(interaction.channel, discord.abc.Messageable):
            await interaction.response.send_message(
                "Cannot post the leaderboard in this channel.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        tournament = TournamentsFile.get_tournament(self.tournament.get("name", ""))
        embed = await build_tournament_detail_embed(interaction, tournament)
        _set_leaderboard_refresh_footer(embed)
        view = LeaderboardPublicView(tournament_name=tournament.get("name", ""))
        try:
            await interaction.channel.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send(
                "Missing permissions to post here. The bot needs **Embed Links** (and **Send Messages**) in this channel. Ask a server admin to enable them.",
                ephemeral=True,
            )
            return
        await interaction.followup.send("Leaderboard posted to the channel.", ephemeral=True)


class LeaderboardPublicView(discord.ui.View):
    """View for the public leaderboard message: refresh button, never times out."""

    def __init__(self, *, tournament_name: str = "") -> None:
        super().__init__(timeout=None)
        self.tournament_name = tournament_name

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, custom_id="leaderboard_public_refresh")
    async def refresh_scores(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Get tournament name from this view or from the message embed (for persistent view after restart)
        name = self.tournament_name
        if not name and interaction.message.embeds:
            name = interaction.message.embeds[0].title or ""
        if not name:
            await interaction.response.send_message(
                "Could not determine which tournament to refresh.",
                ephemeral=True,
            )
            return
        try:
            tournament = TournamentsFile.get_tournament(name)
        except ValueError:
            await interaction.response.send_message(
                "This tournament no longer exists or was renamed.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        # Show loading state immediately (BeatSaver only, no BeatLeader calls)
        loading_embed = await build_tournament_detail_embed(interaction, tournament, loading=True)
        _set_leaderboard_refresh_footer(loading_embed)
        view = LeaderboardPublicView(tournament_name=tournament.get("name", ""))
        await interaction.message.edit(embed=loading_embed, view=view)
        # Fetch real scores then update
        embed = await build_tournament_detail_embed(interaction, tournament)
        _set_leaderboard_refresh_footer(embed)
        await interaction.message.edit(embed=embed, view=view)


class RemovePlayerView(discord.ui.View):
    def __init__(self, tournament: dict, parent_interaction: discord.Interaction) -> None:
        super().__init__(timeout=None)
        self.tournament = tournament
        self.parent_interaction = parent_interaction

        players: dict = tournament.get("players", {}) or {}
        if players:
            self.add_item(
                RemovePlayerSelect(
                    players=players,
                    tournament_name=tournament.get("name", ""),
                    parent_interaction=parent_interaction,
                )
            )


class RemovePlayerSelect(discord.ui.Select):
    def __init__(
        self,
        *,
        players: dict,
        tournament_name: str,
        parent_interaction: discord.Interaction,
    ) -> None:
        self.tournament_name = tournament_name
        self.parent_interaction = parent_interaction

        options: list[discord.SelectOption] = []
        for key, data in players.items():
            username = str(data.get("beatleaderUsername", "Unknown"))
            options.append(
                discord.SelectOption(
                    label=username,
                    value=str(key),
                )
            )

        max_values = max(1, len(options))

        super().__init__(
            placeholder="Select player(s) to remove...",
            min_values=1,
            max_values=max_values,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            tournament = TournamentsFile.get_tournament(self.tournament_name)
        except ValueError:
            await interaction.response.send_message(
                "Tournament could not be found. It may have been removed or renamed.",
                ephemeral=True,
            )
            return

        players: dict = (tournament.get("players") or {}).copy()
        if not players:
            await interaction.response.send_message(
                "There are no players to remove from this tournament.",
                ephemeral=True,
            )
            return

        removed_usernames: list[str] = []
        for key in self.values:
            data = players.pop(key, None)
            if data is not None:
                removed_usernames.append(str(data.get("beatleaderUsername", "Unknown")))

        if not removed_usernames:
            await interaction.response.send_message(
                "No players were removed (selected entries may no longer exist).",
                ephemeral=True,
            )
            return

        TournamentsFile.save_tournament(
            name=self.tournament_name,
            players=players,
        )

        updated_tournament = TournamentsFile.get_tournament(self.tournament_name)
        embed = await build_tournament_detail_embed(interaction, updated_tournament)
        admin_view = TournamentAdminDetailView(updated_tournament, self.parent_interaction)

        await interaction.response.edit_message(
            content=(
                f"Removed {', '.join(removed_usernames)} from "
                f"'{updated_tournament.get('name', '')}'."
            ),
            embed=embed,
            view=admin_view,
        )

class JoinWithUsernameModal(discord.ui.Modal, title='Join Tournament'):
    def __init__(self, parent_view: TournamentDetailView) -> None:
        super().__init__()
        self.parent_view = parent_view
        self.username_input = discord.ui.TextInput(
            label="BeatLeader Username (optional)",
            placeholder="Enter your BeatLeader username, or leave blank to link your Discord at https://beatleader.com/signin/socials",
            max_length=64,
            required=False,
        )
        self.add_item(self.username_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        discord_id = str(interaction.user.id)
        username = self.username_input.value.strip()

        if not username:
            # User chose not to provide a username; remind them to link their account.
            await interaction.response.send_message(
                "You don't have Discord linked in your BeatLeader account. "
                "Link it here: https://beatleader.com/signin/socials",
                ephemeral=True,
            )
            return

        player = await interaction.client.beatleader.get_single_player_by_name(username)
        if not player:
            await interaction.response.send_message(
                f"No BeatLeader player found for username '{username}'.",
                ephemeral=True,
            )
            return

        updated_players = self.parent_view.tournament.get("players", {})
        if discord_id in updated_players:
            await interaction.response.send_message(
                "You are already registered for this tournament.",
                ephemeral=True,
            )
            return

        updated_players[discord_id] = {
            "beatleaderUsername": player.get("name", "Unknown"),
            "beatleaderId": player.get("id"),
        }

        TournamentsFile.save_tournament(
            name=self.parent_view.tournament.get("name", ""),
            players=updated_players,
        )

        updated_tournament = TournamentsFile.get_tournament(self.parent_view.tournament.get("name", ""))
        self.parent_view.tournament = updated_tournament
        self.parent_view.update_buttons()
        embed = await build_tournament_detail_embed(interaction, updated_tournament)

        await interaction.response.defer()
        await self.parent_view.interaction.edit_original_response(
            content=f"You have joined the tournament '{self.parent_view.tournament.get('name', '')}' as {player.get('name', 'Unknown')}.",
            embed=embed,
            view=self.parent_view,
        )

class RegisterPlayerModal(discord.ui.Modal, title='Register Player'):
    def __init__(self, parent_view: TournamentDetailView) -> None:
        super().__init__()
        self.parent_view = parent_view
        self.discord_id_input = discord.ui.TextInput(
            label="Discord ID / Mention / BeatLeader Username(s)",
            placeholder="One per line: Discord mention, Discord ID, or BeatLeader username",
            style=discord.TextStyle.paragraph,
            max_length=1024,
        )
        self.add_item(self.discord_id_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        lines = [
            line.strip()
            for line in self.discord_id_input.value.splitlines()
            if line.strip()
        ]

        if not lines:
            await interaction.response.send_message("No players specified.", ephemeral=True)
            return

        existing_players: dict = self.parent_view.tournament.get("players", {}).copy()
        new_players: dict[str, dict] = {}
        errors: list[str] = []

        for index, raw in enumerate(lines, start=1):
            line = raw
            discord_id: str | None = None

            if line.startswith("<@") and line.endswith(">"):
                inner = line[2:-1]
                if inner.startswith("!"):
                    inner = inner[1:]
                if inner.isdigit():
                    discord_id = inner
            elif line.isdigit():
                discord_id = line

            player = None
            player_key: str | None = None

            if discord_id is not None:
                player = await interaction.client.beatleader.get_player_by_discord_id(discord_id)
                if player:
                    player_key = discord_id

            # Fallback to BeatLeader username search when Discord lookup fails or is not applicable
            if player is None:
                player = await interaction.client.beatleader.get_single_player_by_name(line)
                if not player:
                    errors.append(f"Line {index} ('{raw}'): no BeatLeader player found.")
                    continue

                player_key = str(player.get("id"))

            if player_key is None:
                errors.append(f"Line {index} ('{raw}'): could not resolve player.")
                continue

            if player_key in existing_players or player_key in new_players:
                errors.append(f"Line {index} ('{raw}'): player already registered.")
                continue

            new_players[player_key] = {
                "beatleaderUsername": player.get("name", "Unknown"),
                "beatleaderId": player.get("id"),
            }

        if not new_players:
            if errors:
                message = "No valid players to register.\n" + "\n".join(f"- {e}" for e in errors)
            else:
                message = "No valid players to register."
            await interaction.response.send_message(message, ephemeral=True)
            return

        updated_players = existing_players.copy()
        updated_players.update(new_players)

        TournamentsFile.save_tournament(
            name=self.parent_view.tournament.get("name", ""),
            players=updated_players,
        )

        self.parent_view.tournament = TournamentsFile.get_tournament(self.parent_view.tournament.get("name", ""))
        self.parent_view.update_buttons()
        embed = await build_tournament_detail_embed(interaction, self.parent_view.tournament)

        success_names = ", ".join(str(data.get("beatleaderUsername", "Unknown")) for data in new_players.values())
        content = f"Registered {success_names} for '{self.parent_view.tournament.get('name', '')}'."
        if errors:
            content += "\n\nSome entries could not be registered:\n" + "\n".join(f"- {e}" for e in errors)

        await interaction.response.defer()
        await self.parent_view.interaction.edit_original_response(
            content=content,
            embed=embed,
            view=self.parent_view,
        )

description = "View and edit tournaments."
@app_commands.command(name="tournaments", description=description)
async def tournaments(interaction: discord.Interaction) -> None:
    tournament_ = TournamentsFile.get_tournaments(active=False)
    embed = await build_tournaments_embed(interaction, tournament_)
    view = TournamentView(interaction=interaction)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

def setup(bot: discord.Client) -> None:
    bot.tree.add_command(tournaments)
    # Persistent view so the public leaderboard Refresh button still works after bot restart
    bot.add_view(LeaderboardPublicView(tournament_name=""))
