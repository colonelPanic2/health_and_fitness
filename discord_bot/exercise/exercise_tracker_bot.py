import discord
from discord.ext import commands
from discord import app_commands
import difflib
from exercises import *
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_metadata')))
from exercise_tracker_bot_MDATA import *
os.system('pwd')



class ExerciseTracker(EXERCISE_HISTORY_CLS):
    def __init__(self, PATH):
        super().__init__(PATH)
        self.log_workout = False
        self.workout_exercise_position = None
        self.current_exercise = None
        self.new_workout = None
        self.workout = None
    def cannot_perform_action(self):
        status = bool(
            self.log_workout == False 
            or self.workout_exercise_position is None 
            or self.current_exercise is None 
            or self.new_workout is None 
            or self.workout is None
        )
        return status
    def start_workout(self):
        if self.new_workout is not None and self.workout is not None:
            return f'Finish logging the current workout, "{self.new_workout}", before starting a new workout'
        elif self.new_workout is not None or self.workout is not None:
            return f'ERROR: The bot is in an unexpected state\nworkout_index = {self.new_workout}\nworkout = {self.workout}'
        self.log_workout = True
        self.workout_exercise_position = 0
        self.current_exercise = None
        self.new_workout = self.get_latest_workout() + 1
        self.workout = {}
        return f'Started logging new workout: {self.new_workout}'
    def get_exercise(self, exercise_name):
        if self.cannot_perform_action():
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        exercise_name = re.sub(r'__+','_',exercise_name.upper().strip().replace(' ','_'))
        if not self.exercise_exists(exercise_name):
            return f'"{exercise_name}" doesn\'t exist. Run "/newexercise {exercise_name}"'
        if exercise_name == "DAY_OFF":
            self.workout[self.workout_exercise_position] = {"exercise_name": exercise_name, "stats": {0: 24}}
            self.workout_exercise_position += 1
            self.current_exercise = None
            return "Enjoy your day off!"
        self.current_exercise = exercise_name
        return f'Now logging sets for "{exercise_name}". Run "/sets" to log results'
    def get_sets(self, sets):
        if self.cannot_perform_action():
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            elif self.current_exercise is None or self.workout_exercise_position is None:
                return f'Not currently logging an exercise. Run "/exercise" or "/newexercise"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        sets = re.sub(r'(\d+)[xX](\d+)', r'\1x\2', sets.replace(' ',''))
        sets_list = sets.split(',')
        sets_dict = {}
        msg = ''
        for i,set in enumerate(sets_list):
            if not valid_data_format(self.get_units(self.current_exercise), set):
                msg += f'(SET {i+1}) Invalid entry: "{set}"' + str('\n' if i < len(sets)-1 else '')
            else:
                sets_dict[i] = set
        if msg == '':
            return msg
        self.workout[self.workout_exercise_position] = {'exercise_name': self.current_exercise, 'stats': sets_dict}
        self.workout_exercise_position += 1
        self.current_exercise = None
    def add_new_exercise(self, exercise):
        if self.cannot_perform_action():
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        self.workout[self.workout_exercise_position] = exercise
        self.workout_exercise_position += 1
        self.current_exercise=None
    def get_workout(self):
        if self.cannot_perform_action():
            return None
        return self.workout
    def end_workout(self):
        if self.cannot_perform_action():
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        elif self.workout == "":
            return f'Log at least one exercise before finishing the workout'
        self.add_workout()
        self.log_workout = False
        self.workout_exercise_position = None
        self.current_exercise = None
        self.new_workout = None
        self.workout = None
        return f'Finished logging new workout: {self.new_workout}\nGood job!'

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
EXERCISE_TRACKER = ExerciseTracker(EXERCISE_HISTORY_PATH)

### (start_workout)
@bot.tree.command(name="start_workout", description="Start logging a new workout")
async def start_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.start_workout()
    await interaction.response.send_message(msg)

### (get_exercise) Add a new entry for an existing exercise
async def exercise_autocomplete(interaction: discord.Interaction, current: str):
    matches = difflib.get_close_matches(current, EXERCISE_TRACKER.exercises, n=25, cutoff=0.5)
    return [app_commands.Choice(name=match, value=match) for match in matches]
@bot.tree.command(name="exercise", description="Pick an exercise from a list")
@app_commands.describe(name="Name of the exercise")
@app_commands.autocomplete(name=exercise_autocomplete)
async def exercise(interaction: discord.Interaction, name: str):
    msg = EXERCISE_TRACKER.get_exercise(name)
    await interaction.response.send_message(msg)

### (get_sets)
@bot.tree.command(name="get_sets", description="Add a comma-separated list of the sets for the current exercise")
async def get_sets(interaction: discord.Interaction, sets: str):
    msg = EXERCISE_TRACKER.get_sets(sets)
    await interaction.response.send_message(msg)

### (add_new_exercise) Let the user add a new exercise to the list
class NewExerciseModal(discord.ui.Modal, title="New Exercise"):
    name = discord.ui.TextInput(label="Exercise Name",placeholder="Enter the name of the exercise")
    area = discord.ui.TextInput(label="Target Muscle Area",placeholder='BACK, CHEST, ARMS, LEGS, ABS, N/A')
    units = discord.ui.TextInput(label="Units",placeholder="Leave empty for <N_REPS>x<N_POUNDS>")
    sets = discord.ui.TextInput(label="Sets",placeholder="Comma-separated sets for the new exercise being recorded")
    async def on_submit(self, interaction: discord.Interaction):
        new_exercise = {
            'exercise_name': re.sub(r'__+','_',str(self.name.value).strip().upper().replace(' ','_')),
            'area': str(self.area.value).strip().upper(),
            'units': str(self.units.value).strip(),
            'sets': str(self.sets.value).replace(' ','')
        }
        check_new_exercise_name = re.findall(r'^[A-Z0-9_\-]+$',new_exercise['exercise_name'])
        user_response_valid = (
                EXERCISE_TRACKER.area_exists(new_exercise['area']))\
                and (len(check_new_exercise_name) != 0 and check_new_exercise_name[0] == new_exercise['exercise_name']\
                and valid_data_format(new_exercise['units'], new_exercise['sets'])
            )
        if user_response_valid:
            EXERCISE_TRACKER.add_new_exercise(new_exercise)
        await interaction.response.send_message(f'''Added new exercise, "{new_exercise['exercise_name']}"''')
@bot.tree.command(name="newexercise", description="Define a new exercise and add the first entry")
async def new_exercise(interaction: discord.Interaction):
    await interaction.response.send_modal(NewExerciseModal())

### (end_workout)
@bot.tree.command(name="end_workout", description="Save the current workout. THIS RESETS ALL INPUT DATA FOR THE CURRENT EXERCISE")
async def end_workout(interaction: discord.Interaction):
    msg = EXERCISE_TRACKER.end_workout()
    await interaction.response.send_message(msg)








@bot.event
async def on_ready():
    guild = discord.Object(id=int(GUILD_ID))
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)

