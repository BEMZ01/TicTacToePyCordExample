# using pycord make a bot that plays tictactoe

import discord
from discord import SlashCommand
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import time
import random
import os
import sys
from dotenv import load_dotenv

bot = commands.Bot(guild_ids=[867773426773262346])
# load env file
load_dotenv()


@bot.event
async def on_ready():
    # find commands in cogs
    for cog in bot.cogs:
        print("Registering commands for " + cog)
        await bot.register_commands(bot.get_cog(cog).get_commands())
    print("Bot is ready!")
    print("Name: {}".format(bot.user.name))
    print("ID: {}".format(bot.user.id))

if __name__ == "__main__":
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            name = file[:-3]
            bot.load_extension(f"cogs.{name}")
            print(f"Loaded {name} cog.")
    print("Starting bot...")
    bot.run(os.getenv("TOKEN"))
