import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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

if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN is not set in the .env file.")
        exit(1)
    bot.run(TOKEN)