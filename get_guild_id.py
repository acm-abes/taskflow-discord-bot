# get_guild_id.py

import discord
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in your .env file. Please add it and try again.")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"\nLogged in as: {client.user}")
    print("Guilds the bot is in:\n")

    for guild in client.guilds:
        print(f"{guild.name} → Guild ID: {guild.id}")

    await client.close()

client.run(TOKEN)
