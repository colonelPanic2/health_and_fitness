import discord
from discord.ext import commands
from discord import app_commands
import difflib
from exercises import *
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_metadata')))
from exercise_tracker_bot import TOKEN

class ExerciseTracker(EXERCISE_HISTORY_CLS):
    def __init__(self, PATH, TOKEN):
        super().__init__(PATH)
        self.token = TOKEN
    def run_bot(self):
        self.bot.run(self.token)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
EXERCISE_TRACKER = ExerciseTracker(EXERCISE_HISTORY_PATH)

async def exercise_autocomplete(interaction: discord.Interaction, current: str):
    matches = difflib.get_close_matches(current, EXERCISE_TRACKER.exercises, n=25, cutoff=0.1)
    return [app_commands.Choice(name=match, value=match) for match in matches]
# Slash command with autocomplete
@bot.tree.command(name="exercise", description="Pick an exercise from a list or add a new exercise")
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def exercise(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"You picked: **{name}**")

@bot.event
async def on_ready(self):
    await self.bot.tree.sync()
    print(f"Logged in as {self.bot.user}")

bot.run(TOKEN)


# intents = discord.Intents.default()
# bot = commands.Bot(command_prefix="!", intents=intents)

# # Autocomplete function
# async def exercises_autocomplete(interaction: discord.Interaction, current: str):
#     # Filter options by fuzzy match or startswith (basic example shown)
#     return [
#         app_commands.Choice(name=exercise, value=exercise)
#         for exercise in OPTIONS if current.lower() in fruit.lower()
#     ][:25]  # Discord allows a max of 25 choices

# # Slash command with autocomplete
# @bot.tree.command(name="fruit", description="Pick a fruit from a list")
# @app_commands.describe(name="Name of the fruit")
# @app_commands.autocomplete(name=fruit_autocomplete)
# async def fruit(interaction: discord.Interaction, name: str):
#     await interaction.response.send_message(f"You picked: **{name}**")

# @bot.event
# async def on_ready():
#     await bot.tree.sync()
#     print(f"Logged in as {bot.user}")

# bot.run("YOUR_BOT_TOKEN")
