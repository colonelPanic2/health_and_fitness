from exercises import *
import discord
from discord.ext import commands
from discord import app_commands
import difflib
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_metadata')))
from exercise_tracker_bot_MDATA import *

guild = discord.Object(id=GUILD_ID)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

EXERCISE_TRACKER = ExerciseTracker(EXERCISE_HISTORY_PATH)

class NewExerciseModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="New Exercise")
        self.name = discord.ui.TextInput(label="Exercise Name",placeholder="Enter the name of the exercise")
        self.area = discord.ui.TextInput(label="Target Muscle Area",placeholder='BACK, CHEST, ARMS, LEGS, ABS, N/A')
        self.units = discord.ui.TextInput(label="Units",placeholder="Leave empty for <N_REPS>x<N_POUNDS>",required=False)
        self.sets = discord.ui.TextInput(label="Sets",placeholder="Comma-separated sets for the new exercise being recorded")
        self.add_item(self.name)
        self.add_item(self.area)
        self.add_item(self.units)
        self.add_item(self.sets)
    async def on_submit(self, interaction: discord.Interaction):
        new_exercise = {
            'exercise_name': re.sub(r'__+','_',str(self.name.value).strip().upper().replace(' ','_')),
            'area': str(self.area.value).strip().upper(),
            'units': str(self.units.value).strip(),
            'sets': re.sub(r'(\d+)[xX](\d+)', r'\1x\2', str(self.sets.value).replace(' ','')).split(',')
        }
        check_new_exercise_name = re.findall(r'^[A-Z0-9_\-]+$',new_exercise['exercise_name'])
        user_response_valid = (
                (not EXERCISE_TRACKER.exercise_exists(new_exercise['exercise_name']))
                and EXERCISE_TRACKER.area_exists(new_exercise['area']))\
                and (len(check_new_exercise_name) != 0 and check_new_exercise_name[0] == new_exercise['exercise_name']\
                and all(valid_data_format(new_exercise['units'], set_) for set_ in new_exercise['sets'])
            )
        if user_response_valid:
            msg = EXERCISE_TRACKER.add_new_exercise(new_exercise)
            msg = msg if msg.startswith('Added new') else f'''{msg}\nexercise_name: "{new_exercise['exercise_name']}"\narea: "{new_exercise['area']}"\nunits: "{new_exercise['units']}"\nsets: "{new_exercise['sets']}"'''
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(f'''❌ Invalid input. Please check your values and try again. {user_response_valid}\nexercise_name: "{new_exercise['exercise_name']}"\narea: "{new_exercise['area']}"\nunits: "{new_exercise['units']}"\nsets: "{new_exercise['sets']}"''',ephemeral=True)


### (add_new_exercise) Let the user add a new exercise to the list
@bot.tree.command(name="newexercise", description="Define a new exercise and add the first entry", guild=guild)
async def new_exercise(interaction: discord.Interaction):
    await interaction.response.send_modal(NewExerciseModal())

### (start_workout)
@bot.tree.command(name="start_workout", description="Start logging a new workout", guild=guild)
async def start_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.start_workout()
    await interaction.response.send_message(msg, ephemeral=True)

### (get_exercise) Add a new entry for an existing exercise
async def exercise_autocomplete(interaction: discord.Interaction, current: str):
    matches = difflib.get_close_matches(current, EXERCISE_TRACKER.exercises, n=25, cutoff=0.3)
    return [app_commands.Choice(name=match, value=match) for match in matches]
@bot.tree.command(name="exercise", description="Pick an exercise from a list", guild=guild)
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def exercise(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.get_exercise(name)
    await interaction.response.send_message(msg, ephemeral=True)

### (get_sets)
@bot.tree.command(name="get_sets", description="Add a comma-separated list of the sets for the current exercise", guild=guild)
async def get_sets(interaction: discord.Interaction, sets: str):
    msg = EXERCISE_TRACKER.get_sets(sets)
    await interaction.response.send_message(msg, ephemeral=True)

### (end_workout)
@bot.tree.command(name="end_workout", description="Save the current workout. THIS RESETS ALL INPUT DATA FOR THE CURRENT EXERCISE", guild=guild)
async def end_workout(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = EXERCISE_TRACKER.end_workout()
    await interaction.followup.send(msg, ephemeral=True)



### (abort_workout)
@bot.tree.command(name="abort_workout", description="Stop logging the current workout without saving", guild=guild)
async def abort_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.abort_workout()
    await interaction.response.send_message(msg,ephemeral=True)

### (abort_exercise)
@bot.tree.command(name="abort_exercise", description="Stop logging the current exercise without saving it",guild=guild)
async def abort_exercise(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.abort_exercise()
    await interaction.response.send_message(msg,ephemeral=True)

### (show_workout)
@bot.tree.command(name="show_workout", description="Print your progress in the current workout",guild=guild)
async def show_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.show_workout()
    await interaction.response.send_message(msg,ephemeral=True)

### (get_last_workout_date)
@bot.tree.command(name="last_workout_date", description="Get the timestamp of the most recent workout", guild=guild)
async def last_workout_date(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.get_last_workout_date()
    await interaction.response.send_message(msg,ephemeral=True)

### (get_latest_instance_data)
@bot.tree.command(name="exercise_hist", description="Get the last 1-3 instances of the given workout", guild=guild)
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def exercise(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.get_latest_instance_data(name)
    await interaction.response.send_message(msg, ephemeral=True)

### (_reset_state)
@bot.tree.command(name="restore", description="Restore the bot to its default state",guild=guild)
async def reset_state(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = EXERCISE_TRACKER._reset_state()
    await interaction.followup.send(msg,ephemeral=True)

