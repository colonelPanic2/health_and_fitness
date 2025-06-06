from exercise_commands import *
from schedule_commands import *


@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    # commands = await bot.tree.fetch_commands(guild=guild)
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
