from exercises import *
import discord
from discord.ext import commands
from discord import app_commands
import difflib
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_metadata')))
from exercise_tracker_bot_MDATA import *
import datetime

guild = discord.Object(id=GUILD_ID)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

EXERCISE_TRACKER = ExerciseTracker(EXERCISE_HISTORY_PATH)

class NewExerciseModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="New Exercise")
        self.name = discord.ui.TextInput(label="Exercise Name",placeholder="Enter the name of the exercise")
        self.area = discord.ui.TextInput(label="Target Muscle Area",placeholder='BACK, CHEST, ARMS, LEGS, ABS')
        self.units = discord.ui.TextInput(label="Units",placeholder="Leave empty for <N_REPS>x<N_POUNDS>",required=False)
        self.sets = discord.ui.TextInput(label="Sets",placeholder="Comma-separated sets for the new exercise being recorded")
        self.add_item(self.name)
        self.add_item(self.area)
        self.add_item(self.units)
        self.add_item(self.sets)
    async def on_submit(self, interaction: discord.Interaction):
        new_exercise = {
            'exercise_name': process_exercise_name(self.name.value),#re.sub(r'__+','_',str(self.name.value).strip().upper().replace(' ','_')),
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

class RenameExerciseModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Rename Exercise")
        self.name = discord.ui.TextInput(label="Exercise Name",placeholder="The new name of the existing exercise")
        self.area = discord.ui.TextInput(label="Target Area",placeholder="BACK, CHEST, ARMS, LEGS, ABS",required=False)
        # self.new_muscle_group = discord.ui.TextInput(label="Muscle groups",placeholder="The name(s) of the muscle group(s) being targetted in CSV format")
        self.add_item(self.name)
        self.add_item(self.area)
        # self.add_item(self.new_muscle_group)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        renamed_exercise = {
            'exercise_name': process_exercise_name(self.name.value),
            'area': str(self.area.value).strip().upper(),
            # 'new_muscle_groups': [re.sub(r'__+','_',str(new_muscle_group).replace(' ','_').strip('_')) for new_muscle_group in str(self.new_muscle_group.value).split(',')]
        }
        check_new_exercise_name = re.findall(r'^[A-Z0-9_\-]+$',renamed_exercise['exercise_name'])
        user_response_valid = (
            (not EXERCISE_TRACKER.exercise_exists(renamed_exercise['exercise_name']))
            and EXERCISE_TRACKER.area_exists(renamed_exercise['area'])
            and (len(check_new_exercise_name) != 0 and check_new_exercise_name[0] == renamed_exercise['exercise_name'])
        )
        if user_response_valid:
            msg = EXERCISE_TRACKER.rename_exercise(renamed_exercise)
            if msg.startswith('Finished renaming exercise: '):
                user_id = interaction.user.id
                user = await bot.fetch_user(user_id)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                zip_stream = EXERCISE_TRACKER._get_backup()
                hist_file = File(fp=zip_stream, filename=f'exercise_history_{timestamp}.zip')
                await user.send(f'Backup timestamp: {timestamp}', file=hist_file)
            else:
                msg = f'''{msg}\nexercise_name: "{renamed_exercise['exercise_name']}"\narea: "{renamed_exercise['area']}"'''
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.followup.send(f'''❌ Invalid input. Please check your values and try again. {user_response_valid}\nexercise_name: "{renamed_exercise['exercise_name']}"\narea: "{renamed_exercise['area']}"''',ephemeral=True)

async def exercise_autocomplete(interaction: discord.Interaction, current: str):
    current = process_exercise_name(current)
    matches = difflib.get_close_matches(current, EXERCISE_TRACKER.exercises, n=25, cutoff=0.3)
    return [app_commands.Choice(name=match, value=match) for match in matches]

### (select_exercise) Choose an exercise to modify or review
@bot.tree.command(name="select_exercise_rename", description="Pick an exercise from a list", guild=guild)
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def _select_exercise_rename(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.select_exercise(name, select_mode="RENAME")
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name='rename_exercise',description="Let the user enter new values for the exercise currently being renamed",guild=guild)
async def rename_exercise(interaction: discord.Interaction):
    await interaction.response.send_modal(RenameExerciseModal())

### (add_new_exercise) Let the user add a new exercise to the list
@bot.tree.command(name="new_exercise", description="Define a new exercise and add the first entry", guild=guild)
async def new_exercise(interaction: discord.Interaction):
    await interaction.response.send_modal(NewExerciseModal())

### (start_workout)
@bot.tree.command(name="start_workout", description="Start logging a new workout", guild=guild)
async def start_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.start_workout()
    await interaction.response.send_message(msg, ephemeral=True)

### (get_exercise) Add a new entry for an existing exercise
@bot.tree.command(name="exercise", description="Pick an exercise from a list", guild=guild)
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def exercise(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.get_exercise(name)
    # await interaction.response.send_message(msg, ephemeral=True)
    if msg.startswith('Finished logging new workout'):
        user_id = interaction.user.id
        user = await bot.fetch_user(user_id)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_stream = EXERCISE_TRACKER._get_backup()
        hist_file = File(fp=zip_stream, filename=f'exercise_history_{timestamp}.zip')
        await interaction.response.send_message(msg, ephemeral=True)
        await user.send(f'Backup timestamp: {timestamp}', file=hist_file)
    elif msg.startswith(f'ERROR:'):
        await interaction.response.send_message(msg, ephemeral=True)
    else:
        msg2 = EXERCISE_TRACKER.get_latest_instance_data(name)
        if type(msg2) == str:
            await interaction.response.send_message(msg2, ephemeral=True)
        else:
            name = process_exercise_name(name)
            await interaction.response.send_message(msg, file=msg2, ephemeral=True)
### (get_sets)
@bot.tree.command(name="sets", description="Add a comma-separated list of the sets for the current exercise", guild=guild)
async def get_sets(interaction: discord.Interaction, sets: str):
    msg = EXERCISE_TRACKER.get_sets(sets)
    await interaction.response.send_message(msg, ephemeral=True)

### (end_workout)
@bot.tree.command(name="end_workout", description="Save the current workout. THIS RESETS ALL INPUT DATA FOR THE CURRENT EXERCISE", guild=guild)
async def end_workout(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = EXERCISE_TRACKER.end_workout()
    await interaction.followup.send(msg, ephemeral=True)
    if msg.startswith('Finished logging new workout'):
        user_id = interaction.user.id
        user = await bot.fetch_user(user_id)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_stream = EXERCISE_TRACKER._get_backup()
        hist_file = File(fp=zip_stream, filename=f'exercise_history_{timestamp}.zip')
        await user.send(f'Backup timestamp: {timestamp}', file=hist_file)
    


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
async def exercise_hist(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.get_latest_instance_data(name)
    if type(msg) == str:
        await interaction.response.send_message(msg, ephemeral=True)
    else:
        name = process_exercise_name(name)
        await interaction.response.send_message(name, file=msg, ephemeral=True)

### (_reset_state)
@bot.tree.command(name="restore", description="Restore the bot to its default state",guild=guild)
async def reset_state(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = EXERCISE_TRACKER._reset_state()
    await interaction.followup.send(msg,ephemeral=True)

### (_get_backup)
@bot.tree.command(name='backup', description='Save the history as a zipped CSV file',guild=guild)
async def send_backup(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = interaction.user.id
    user = await bot.fetch_user(user_id)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_stream = EXERCISE_TRACKER._get_backup()
    hist_file = File(fp=zip_stream, filename=f'exercise_history_{timestamp}.zip')
    await interaction.followup.send(f"Backup timestamp: {timestamp}", ephemeral=True)
    await user.send(f"Backup timestamp: {timestamp}", file=hist_file)

### (change_sets)
async def logged_exercise_autocomplete(interaction: discord.Interaction, current: str):
    current = process_exercise_name(current)
    matches = difflib.get_close_matches(current, [ f'{index} - {data["exercise_name"]}' for index, data in EXERCISE_TRACKER.workout.items()], n=25, cutoff=0.0)
    return [app_commands.Choice(name=match, value=match) for match in matches]
@bot.tree.command(name="change_sets", description="Change the sets for a completed exercise in the current workout",guild=guild)
@app_commands.describe(name="Name (and instance) of exercise")
@app_commands.autocomplete(name=logged_exercise_autocomplete)
async def change_sets(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.change_sets(name)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="show_selected", description="Show the currently selected exercises/features",guild=guild)
async def show_selected(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.show_selected()
    await interaction.response.send_message(msg, ephemeral=True)
