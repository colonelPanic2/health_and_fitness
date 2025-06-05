import discord
from discord.ext import commands
from discord import app_commands
import difflib
from exercises import *
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_metadata')))
from exercise_tracker_bot_MDATA import *
if not platform.startswith('win'):
    os.system('pwd')
guild = discord.Object(id=GUILD_ID)


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
        exercise_name = re.sub(r'__+','_',exercise_name.upper().strip().replace(' ','_'))
        if self.workout_exercise_position is None:
            self.workout_exercise_position = 0
        if self.current_exercise is None:
            self.current_exercise = exercise_name
        if self.cannot_perform_action():
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
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
        if msg != '':
            return msg
        else:
            msg = f'({self.workout_exercise_position+1}) "{self.current_exercise}" - {", ".join(sets_list)}'
        self.workout[self.workout_exercise_position] = {'exercise_name': self.current_exercise, 'stats': sets_dict}
        self.workout_exercise_position += 1
        self.current_exercise = None
        return msg
    def add_new_exercise(self, exercise):
        self.current_exercise = exercise['exercise_name']
        if self.cannot_perform_action():
            self.current_exercise = None
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        self.new_exercises[self.current_exercise] = {'units': exercise['units'], 'area': exercise['area']}
        self.exercises.append(exercise['exercise_name'])
        exercise_log = {'exercise_name': exercise['exercise_name'], 'stats': {i: set_ for i,set_ in enumerate(exercise['sets'])}}
        self.workout[self.workout_exercise_position] = exercise_log
        self.workout_exercise_position += 1
        self.current_exercise=None
        return f'''Added new exercise:\n"({self.workout_exercise_position}) {exercise['exercise_name']}" - {", ".join(exercise["sets"])}'''
    def get_workout(self):
        # Defined for the definition of "add_workout" in exercises.py
        return self.workout
    def end_workout(self):
        if self.workout is not None and self.workout == {}:
            self.log_workout = False
            self.workout_exercise_position = None
            self.current_exercise = None
            self.new_workout = None
            self.workout = None
            return f'ABORT: Stopped logging exercise "{self.new_workout}" without saving'
        if self.log_workout == False or self.workout is None or self.new_workout is None:
            return f'Not currently logging a workout. Run "/start_workout"'
        self.add_workout()
        new_workout = self.new_workout
        self.log_workout = False
        self.workout_exercise_position = None
        self.current_exercise = None
        self.new_workout = None
        self.workout = None
        return f'Finished logging new workout: {new_workout}\nGood job!'
    def abort_workout(self):
        if self.new_workout is None:
            return f'Not currently logging a workout. Run "/start_workout"'
        msg = f'Aborted logging workout {self.new_workout}'
        self.log_workout = False
        self.workout_exercise_position = None
        self.current_exercise = None
        self.new_workout = None
        self.workout = None
        return msg
    def abort_exercise(self):
        if self.new_workout is None or self.log_workout == False:
            return f'Not currently logging a workout. Run "/start_workout"'
        elif self.current_exercise is None:
            return f'Not currently logging an exercise for workout "{self.new_workout}". Run "/exercise" or "/newexercise"'
        msg = f'ABORT: Stopped logging "{self.current_exercise}" for workout "{self.new_workout}"'
        self.current_exercise = None
        return msg
    def show_workout(self):
        if self.new_workout is None:
            return 'Not currently logging a workout. Run "/start_workout"'
        elif self.workout is None or self.workout == {} and (self.workout_exercise_position is None and self.current_exercise is None):
            return f'No exercises logged for workout {self.new_workout}'
        elif self.workout is None or self.workout == {}:
            return f'WORKOUT_{self.new_workout} = {{}}\nCURRENT_EXERCISE = "{self.current_exercise}"'
        return f'WORKOUT_{self.new_workout} = {json.dumps(self.workout,indent=4)};\nCURRENT_EXERCISE = "{self.current_exercise}"'
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
            await interaction.response.send_message(f"❌ Invalid input. Please check your values and try again.",ephemeral=True)


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


@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    # commands = await bot.tree.fetch_commands(guild=guild)
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
