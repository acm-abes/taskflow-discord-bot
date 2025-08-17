import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("taskflow-bot")

# Set up bot intents (minimal - no privileged intents needed)
intents = discord.Intents.default()

# Create bot instance with command prefix and intents
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s): {[g.name for g in bot.guilds]}")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Slash command for ping (no privileged intents needed)
@bot.tree.command(name="ping", description="Check if the bot is responsive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Fallback message command (requires Message Content Intent to be enabled)
@bot.command(name="ping", help="Check if the bot is responsive.")
async def ping_message(ctx: commands.Context):
    await ctx.send("Pong!")

@bot.tree.command(name="ticket", description="Create a new support ticket.")
@app_commands.describe(reason="Reason for opening the ticket")
async def ticket_slash(interaction: discord.Interaction, reason: str = None):
    # Defer the response to avoid timeout
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)
    ticket_name = f"ticket-{interaction.user.name}".lower()

    existing = discord.utils.get(guild.channels, name=ticket_name)
    if existing:
        await interaction.followup.send(f"You already have a ticket: {existing.mention}", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    staff_role = guild.get_role(STAFF_ROLE_ID)
    overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_channel = await guild.create_text_channel(
        name=ticket_name,
        category=category,
        overwrites=overwrites
    )

    await ticket_channel.send(
        f"Hello {interaction.user.mention}, will assist you shortly.\n"
        f"Reason: {reason if reason else 'No reason provided.'}"
    )
    await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="close", description="Close the current ticket (staff only).")
async def close_slash(interaction: discord.Interaction):
    staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("You don’t have permission to close tickets.", ephemeral=True)
        return

    if interaction.channel.name.startswith("ticket-"):
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN is not set in the .env file.")
        exit(1)
    bot.run(TOKEN)