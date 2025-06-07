import pandas as pd
import json
import sys, os
import re
from tabulate import tabulate

EXERCISE_RELATIVE_PATH = 'data/exercise_logs/exercise_history.csv'
EXERCISE_HISTORY_PATH = str('C:/Files/Fitness/' if sys.platform.startswith('win') else '/home/luis/Documents/Fitness/') + EXERCISE_RELATIVE_PATH
PRIMARY_KEYS = ['exercise','area','instance','workout','position','set']

def print_list(inp_list,title=''):
    if title != '':
        title = title+': \n'
    print(title + '\t' + '\n\t'.join([f"""({' '*(len(str(len(inp_list)))-len(str(i+1)))}{i+1} / {len(inp_list)}) {element}""" for i,element in enumerate(inp_list)]))
def set_to_string(set,units):
    if units == '':
        return f'{set[0]}x{set[1]}'
    else:
        return set
def string_to_set(set,units):
    if units == '':
        return [{set.split("x")[0].strip()}, set.split("x")[1].strip()]
    else:
        return set
def stringify_stats(history_stats, units):
    if units=='':
        return ", ".join([f'{REPS_WEIGHT_LBS[0]}x{REPS_WEIGHT_LBS[1]}' for REPS_WEIGHT_LBS in history_stats])
    else:
        return ", ".join([str(element) for element in history_stats])
def levenshtein_distance(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                cost = 0
            else:
                cost = 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[m][n]
def sort_by_distances(input_str, str_list, get_top_k = None):
    str_list = [str(element) for element in str_list]
    if get_top_k is None:
        get_top_k = len(str_list)
    get_distances = [[element, levenshtein_distance(input_str, element)] for element in str_list]
    get_distances = sorted(get_distances, key=lambda x: x[1])
    df_distances = pd.DataFrame({'str_element': [str_distance[0] for str_distance in get_distances], 'distance': [str_distance[1] for str_distance in get_distances]})
    df_distances['input_str'] = [input_str]*len(df_distances)
    return df_distances.head(get_top_k)
def valid_data_format(units, set_entry):
    return bool( (units == '' and re.match(r'^\d+x\d+$',set_entry)) or (units != '' and re.match(r'^\d+$',set_entry)) )
def process_exercise_name( exercise_name):
    return re.sub(r'__+','_',str(exercise_name).strip().upper().replace(' ','_')).strip('_'),
# SW-LT : Shoulder_width-legs_together, each variation gets 1/2 the reps

class EXERCISE_HISTORY_CLS():
    def __init__(self,PATH):
        self.path = PATH
        self.primary_keys = PRIMARY_KEYS
        self.refresh_data()
    def refresh_data(self):
        if not os.path.exists(self.path):
            self.data = pd.DataFrame(['exercise','area','instance','workout','position','set','data','units','dw_mod_ts'])
        else:
            self.data = pd.read_csv(self.path,keep_default_na=False)
        if 'instance' in self.data.columns:
            self.data['instance'] = pd.to_numeric(self.data['instance'], errors='coerce').fillna(-1).astype(int)
        self.exercises = sorted(list(set(self.data['exercise'].tolist())))
        self.areas = list(set(self.data['area'].tolist()))
        self.units = list(set(self.data[self.data['units'].apply(lambda x: pd.notna(x) and str(x).strip()!='')]['units'].tolist()))
        self.workouts = list(set(self.data['workout'].tolist()))
        self.get_latest_workout()
        self.new_exercises = {}
    ### NOTE: Functions for getting data from the dataset
    def get_units(self, exercise):
        if not self.exercise_exists(exercise):
            return None
        units = self.data.query(f'exercise == "{exercise}"')['units']#.tolist()
        if units.empty:
            return None
        units = units.tolist()[0]
        if pd.isna(units) or str(units).strip() == '':
            return ''
        else:
            return units
    def get_area(self, exercise):
        if not self.exercise_exists(exercise):
            return None
        area = self.data.query(f'exercise == "{exercise}"')['area']#.tolist()
        if area.empty:
            return None
        area = area.tolist()[0]
        return area
    def get_latest_instance(self, exercise):
        if not self.exercise_exists(exercise):
            return -1
        instance = self.data.query(f'exercise == "{exercise}"')['instance'].max()
        return instance
    def get_latest_workout(self):
        self.latest_workout = max(self.workouts)
        return self.latest_workout
    ### NOTE: Functions for helping the user set up input data for the dataset
    def get_user_input(self, condition_function, show_similar=None, prompt=None):
        prompt = str('' if prompt is None else f'{prompt}: ')
        user_input = None
        while user_input is None or not condition_function(user_input):
            user_input = input(prompt)
            if not condition_function(user_input):
                print(f'\t- WARNING: INVALID ENTRY "{user_input}"')
                if show_similar:
                    show_similar(user_input)
        return user_input
    def get_exercise(self):
        # Get the name of the existing exercise. If it is a new exercise, then get its name, target area, and units
        show_similar = lambda entry: print(sort_by_distances(entry, self.exercises, get_top_k=5))
        exercise_condition = lambda exercise: exercise != "" and ((len(re.findall(r'[A-Z0-9_\-]+',exercise)) != 0 and str(re.findall(r'[A-Z0-9_\-]+',exercise)[0]) == exercise))
        exercise_name = re.sub(r'\s+', '_', self.get_user_input(exercise_condition, show_similar, prompt = "EXERCISE NAME"))
        if (not self.exercise_exists(exercise_name)):
            add_new_exercise_query_condition = lambda add_new_exercise_yn: True if add_new_exercise_yn.upper().strip() in ('Y','N') else False
            user_add_new_exercise = self.get_user_input(add_new_exercise_query_condition,prompt=f'Add new exercise, "{exercise_name}" (Y/N)?').upper().strip()
            if user_add_new_exercise == "N":
                return None
            # exercise_condition_NEW = lambda exercise: False if exercise != "" and (self.exercise_exists(exercise) or len(re.findall(r'[A-Z0-9_\-]+',exercise)) == 0 or str(re.findall(r'[A-Z0-9_\-]+',exercise)[0]) != exercise) else True
            # show_similar = lambda entry: print(sort_by_distances(entry, self.exercises, get_top_k=10))
            # exercise_name = self.get_user_input(exercise_condition_NEW, show_similar, prompt = "NEW EXERCISE NAME (leave blank to exit new exercise setup)")
            if exercise_name == "":
                return None
            area_condition = lambda area: area=='N/A' or (self.area_exists(area) and (len(re.findall(r'[A-Z0-9_\-]+',area)) != 0 and str(re.findall(r'[A-Z0-9_\-]+',area)[0]) == area))
            show_similar = lambda entry: print(sort_by_distances(entry, self.areas, get_top_k = 3))
            area = self.get_user_input(area_condition, show_similar, prompt="TARGET_MUSCLE_AREA")
            units_condition = lambda units: units=='' or (len(re.findall(r'[a-zA-Z0-9_\-\\]+',units)) != 0 and str(re.findall(r'[a-zA-Z0-9_\-\\]+',units)[0]) == units)
            show_similar = lambda entry: print(sort_by_distances(entry, self.units, get_top_k = 3))
            units = self.get_user_input(units_condition, show_similar, prompt="UNITS (leave blank for '<N_REPS>x<N_POUNDS>')")
            self.add_new_exercise({exercise_name: {"area": area, "units": units}})
        else:
            units = self.get_units(exercise_name)
        # Get the data for the exercise (all sets)
        n_sets_condition = lambda user_n_sets: True if re.match(r'^\d+$',user_n_sets) else False 
        num_sets = int(self.get_user_input(n_sets_condition, prompt="NUMBER OF SETS"))
        sets_list = {}
        valid_format = lambda entry: valid_data_format(units, entry)
        if exercise_name != "DAY_OFF":
            for set_idx in range(num_sets):
                sets_list[set_idx] = self.get_user_input(valid_format, prompt=f"\tSET {set_idx}")
            change_set_condition = lambda user_input: True if str(user_input).upper().strip() in ("Y","N") else False
            user_change_sets = self.get_user_input(change_set_condition, prompt="Would you like to change any sets (Y/N)?")
            valid_set = lambda entry: True if re.match(r'^\d+$', entry) and 0<=int(entry)<=num_sets else False
            while user_change_sets == "Y":
                user_set_index = int(self.get_user_input(valid_set, prompt=f"Which set would you like to change (0-{num_sets-1} OR {num_sets} to exit set change)?"))
                if user_set_index != num_sets:
                    sets_list[user_set_index] = self.get_user_input(valid_format, prompt=f"\tSET {user_set_index}")
                else:
                    break
                user_change_sets = self.get_user_input(change_set_condition, prompt="Would you like to change any sets (Y/N)?")
        else:
            sets_list = {0: '24'}
        return {'exercise_name': exercise_name, 'stats': sets_list}
    def get_workout(self):
        position_index = 0
        workout = {}
        exercises = {}
        yn_condition = lambda entry: True if entry.upper().strip() in ('Y','N') else False
        oad_condition = lambda entry: True if entry.upper().strip() in ('O','A','D') else False
        new_workout = self.get_latest_workout() + 1
        print_list(self.exercises,title='Available Exercises')
        while True:
            exercise_data = self.get_exercise()
            if exercise_data is None:
                abort_setup = self.get_user_input(yn_condition, prompt=f"Abort setup for workout {new_workout} (Y/N)?")
                if abort_setup == "Y":
                    return None
            elif exercise_data['exercise_name'] in exercises:
                exercise_name = exercise_data['exercise_data']
                overwrite_entry = self.get_user_input(oad_condition, prompt=f'''Exercise "{exercise_name}" already exists in position(s) {exercises[exercise_name]}. Overwrite previous version, add new version, or discard new entry (O/A/D)?''')
                if overwrite_entry == 'O':
                    overwrite_index = max(list(exercises[exercise_name]))
                    workout[overwrite_index] = exercise_data
                elif overwrite_entry == 'A':
                    workout[position_index] = exercise_data
                    exercises[exercise_name].add(position_index)
                    position_index += 1
            else:
                workout[position_index] = exercise_data
                exercise_name = exercise_data['exercise_name']
                exercises[exercise_name] = set([position_index])
                position_index += 1
            get_next_exercise = self.get_user_input(yn_condition, prompt=f"Get new exercise (Y/N)?")
            if get_next_exercise == "N":
                break
        print(f'\n\nWORKOUT_{new_workout} = {json.dumps(workout, indent=4)}\n\nWorkout logged: {new_workout}')
        if workout == {}:
            return None
        else:
            return workout
    ### NOTE: Functions for adding data to the dataset
    def add_new_exercise(self, exercise):
        """
        exercise: { "<EXERCISE_NAME>": {"area": "<TARGET_MUSCLE_AREA>", "units": "<UNITS>"}, ... }
        """
        for exercise_name, data in exercise.items():
            self.new_exercises[exercise_name] = data
    def add_workout(self):
        """
        workout: {<POSITION_INDEX>: {"exercise_name": "<EXERCISE_NAME>", "stats": {}}}
        """
        workout = self.get_workout()
        if workout is None:
            print(f'\nABORT: No new workout data was added')
            return 1
        latest_workout_idx = self.latest_workout
        new_workout_idx = latest_workout_idx + 1
        df_workout = pd.DataFrame()
        for position_idx in range(1,len(workout)+1):
            exercise_name = workout[position_idx-1]['exercise_name']
            new_instance  = self.get_latest_instance(exercise_name) + 1
            units         = self.get_units(exercise_name)
            area          = self.get_area(exercise_name)
            if self.adding_exercise(exercise_name):
                units = self.new_exercises[exercise_name]['units']
                area  = self.new_exercises[exercise_name]['area']
            df_tmp = pd.DataFrame({'exercise': [exercise_name], 'area': [area], 'instance': [new_instance], 'workout': [new_workout_idx], 'position': [position_idx], 'units': [units], 'sets_data': [[[i,set_data] for i,set_data in workout[position_idx-1]['stats'].items()]]})
            df_tmp = df_tmp.explode('sets_data').reset_index(drop=True)
            df_tmp['set'] = df_tmp['sets_data'].apply(lambda x: int(x[0]))
            df_tmp['data'] = df_tmp['sets_data'].apply(lambda x: str(x[1]))
            df_tmp = df_tmp.drop(columns=['sets_data'])
            df_workout = pd.concat([df_workout,df_tmp])
        if 'dw_mod_ts' not in self.data.columns:
            self.data['dw_mod_ts'] = None
        df_workout['dw_mod_ts'] = pd.Timestamp.now()
        df_workout = pd.concat([self.data,df_workout]).reset_index(drop=True)[['exercise','area','instance','workout','position','set','data','units','dw_mod_ts']]
        df_workout.to_csv(self.path,index=False)
        self.new_exercises = {}
        return 0
    ### NOTE: Functions for reviewing the data in the dataset
    def print_exercise_history_summary(self):
        full_output = 'EXERCISE_SUMMARY:\n\n'
        for EXERCISE in self.exercises:
            df_tmp = self.data.query(f"exercise == '{EXERCISE}'").sort_values(by=self.primary_keys)
            units = df_tmp['units'].drop_duplicates().tolist()[0]
            df_tmp_agg = df_tmp[self.primary_keys[:-1]+['units']+['data']].groupby(self.primary_keys[:-1]+['units']).agg({'data': lambda x: ', '.join([str(x_) for x_ in x.tolist()])}).reset_index()
            # full_output += f'{EXERCISE}{str(" ( "+row["units"]+" ) " if (pd.notna(row["units"]) and str(row["units"]).strip()!='') else "")}:\n\t'
            full_output += f'{EXERCISE}{str(" ( "+units+" ) " if (pd.notna(units) and str(units).strip()!='') else "")}:\n\t'
            for i, row in df_tmp_agg.iterrows():
                full_output += f"""{' '*(len(str(len(df_tmp_agg)))-len(str(int(row['instance'])+1)))}({int(row['instance'])+1}) : ({row['position']}) {row['data']}"""
                full_output += str('\n\t' if int(row['instance'])+1 < len(df_tmp_agg) else '\n')
            full_output += '\n'
        print(full_output)
    def exercise_exists(self, exercise_name):
        return exercise_name in self.exercises
    def area_exists(self, area):
        return area in self.areas
    def unit_exists(self, unit):
        return unit in self.units
    def adding_exercise(self, exercise_name):
        return exercise_name in self.new_exercises


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
        exercise_name = process_exercise_name(exercise_name)#re.sub(r'__+','_',exercise_name.upper().strip().replace(' ','_'))
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
        _ = self._reset_state()
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
    def get_last_workout_date(self):
        last_workout_index = self.get_latest_workout()
        df = self.data.query('workout == @last_workout_index')[['workout','dw_mod_ts']].head(1)
        if df.empty:
            return "No data found for this exercise."
        # Convert DataFrame to string with tabulate for better formatting
        try:
            table = tabulate(df, headers='keys', tablefmt='github', showindex=False)
        except ImportError:
            table = df.to_string(index=False)
        return f"```\n{table}\n```"
    def get_latest_instance_data(self, exercise):
        latest_instance_index = int(float(self.get_latest_instance(exercise)))
        top_3_range = list(range(max(0,latest_instance_index-2),latest_instance_index+1))
        # Format the DataFrame as a code block for Discord
        df = self.data.query('exercise == @exercise and instance in @top_3_range')[['exercise','instance','position','set','data']]
        if df.empty:
            return "No data found for this exercise."
        # Convert DataFrame to string with tabulate for better formatting
        try:
            table = tabulate(df, headers='keys', tablefmt='github', showindex=False)
        except ImportError:
            table = df.to_string(index=False)
        return f"```\n{table}\n```"
    def _reset_state(self):
        try:
            ### Reset the ExerciseTracker attributes to their default states
            self.log_workout = False
            self.workout_exercise_position = None
            self.current_exercise = None
            self.new_workout = None
            self.workout = None
            ### Reset the EXERCISE_HISTORY_CLS attributes to their default states
            self.refresh_data()
            return f'Bot state restored successfully'
        except Exception as e:
            return f"FATAL ERROR: COULDN'T RESTORE THE BOT TO IT'S DEFAULT STATE."


exercises_by_area = {
    'LEGS': {
        'SINGLE_LEG_PRESS': {
            'metadata': {
                'recommended_sets': 3,
                'recommended_reps': 8,
                'variations': {} # '<variation>': {'visual': '<link-or-image-ref>', 'muscle_groups': {'<muscle_group_1_name>': '<link-or-image-ref>', ...} }
            }
        },
        'SINGLE_LEG_PRESS': {
            'metadata': {
                'recommended_sets': 3,
                'recommended_reps': 8,
                'variations': {} # '<variation>': {'visual': '<link-or-image-ref>', 'muscle_groups': {'<muscle_group_1_name>': '<link-or-image-ref>', ...} }
            }
        },
    }
}
## NOTE: If no 'units' are provided, then the units are [<N_REPS>,<N_POUNDS>]
# exercise_history = {
#     'SINGLE_LEG_PRESS': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[8,40], [8,45], [8,50]], 'workout': 0, 'position': 1},
#             1: {'stats': [[8,70], [8,75]], 'workout': 10, 'position': 5},
#         }
#     },
#     'STANDING_CALF_RAISE': {
#         'area': 'LEGS',
#         'history': {
# 			 0: {'stats': [[15,130], [15,120], [15,115]], 'workout': 0, 'position': 2},
#              1: {'stats': [[15,110], [15,130], [15,140]], 'workout': 6, 'position': 2},
#         }
#     },
#     'SEATED_LEG_CURL': {
#         'area': 'LEGS',
#         'history': {
# 			 0: {'stats': [[12,160], [12,160], [12,160], [12,180]], 'workout': 0, 'position': 3},
#              1: {'stats': [[12,180], [12,200], [12,200], [12,200]], 'workout': 5, 'position': 2},
#              2: {'stats': [[12,200],[12,200],[12,220],[12,200]], 'workout': 6, 'position': 4},
#         }
#     },
#     'KETTLEBELL_SQUAT': {
#         'area': 'LEGS',
#         'history': {
# 			 0: {'stats': [[12,35], [12,50], [10,50]], 'workout': 0, 'position': 4},
#         }
#     },
#     'PLANK': {
#         'area': 'ABS',
#         'units': 'seconds',
#         'history': {
# 			 0: {'stats': [60, 60], 'workout': 0, 'position': 5},
#              1: {'stats': [60], 'workout': 2, 'position': 6}
#         }
#     },
#     '6-IN_HOLD': {
#         'area': 'ABS',
#         'units': 'seconds',
#         'history': {
# 			 0: {'stats': [60, 60], 'workout': 0, 'position': 6},
#         }
#     },
#     'INCLINED_BENCH_PRESS': {
#         'area': 'CHEST',
#         'history': {
# 			 0: {'stats': [[8,105], [8,95], [8,95], [8,95]], 'workout': 1, 'position': 1},
#              1: {'stats': [[8,95], [10,95], [8,100],[5,100]], 'workout': 3, 'position': 1},
#         }
#     },
#     'LAT_PULLDOWN': {
#         'area': 'BACK',
#         'history': {
# 			 0: {'stats': [[12,70], [12,80], [12,80], [12,85]], 'workout': 1, 'position': 2},
#              1: {'stats': [[12,95],[12,105],[12,110]], 'workout': 4, 'position': 2},
#              2: {'stats': [[12,90],[12,85],[12,85]], 'workout': 9, 'position': 4},
#         }
#     },
#     'CLOSE_GRIP_EZ_BAR_CURL': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[12,50],[12,50],[12,50]], 'workout': 1, 'position': 3},
#         }
#     },
#     'BARBELL_SHRUG': {
#         'area': 'BACK',
#         'history': {
#             0: {'stats': [[15,70], [15,70], [15,60]], 'workout': 1, 'position': 4},
#             1: {'stats': [[15,60],[15,80],[15,80]], 'workout': 4, 'position': 4},
#             2: {'stats': [[15,80],[15,90],[15,100]], 'workout': 9, 'position': 3},
#         }
#     },
#     'CHIN_UP_MACHINE': {
#         'area': 'BACK',
#         'history': {
#             0: {'stats': [[10,80],[12,90],[12,90]], 'workout': 1, 'position': 5},
#             1: {'stats': [[12,80],[12,85],[10,75]], 'workout': 9, 'position': 2},
#         }
#     },
#     'BICEPS_CURL_MACHINE': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[12,80],[12,70],[12,70]], 'workout': 1, 'position': 6},
#             1: {'stats': [[8,70],[12,60],[12,60]], 'workout': 8, 'position': 5},
#         }
#     },
#     'LEG_EXTENSION': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[10,80],[10,90],[10,100],[10,120]], 'workout': 2, 'position': 1},
#             1: {'stats': [[8,90],[8,110],[8,120],[8,135]], 'workout': 5, 'position': 1},
#             2: {'stats': [[10,135],[10,140],[10,140],[8,140]],'workout': 6, 'position': 3},
#             3: {'stats': [[10,135],[10,135],[10,135],[10,135]], 'workout': 10, 'position': 1},
#         }
#     },
#     'STANDING_LEG_CURL': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[12,55],[12,55],[12,55]], 'workout': 2, 'position': 2},
#         }
#     },
#     'DUMBBELL_BULGARIAN_SPLIT_SQUAT': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[12,30],[12,30]], 'workout': 2, 'position': 3},
#             1: {'stats': [[12,35],[12,35]], 'workout': 10, 'position': 6},
#         }
#     },
#     'DUMBBELL_GOBLET_SQUAT': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[15,30],[15,30],[15,30]], 'workout': 2, 'position': 4},
#             1: {'stats': [[10,40],[15,40],[15,40]], 'workout': 10, 'position': 4},
#         }
#     },
#     'PUSH_UPS': {
#         'area': 'CHEST',
#         'units': 'push_up',
#         'history': {
#             0: {'stats': [12, 12], 'workout': 2, 'position': 5},
#             1: {'stats': [10,10,10],'workout': 7, 'position': 1},
#         }
#     },
#     'DUMBBELL_OVERHEAD_TRICEP_EXTENSIONS': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[15,10], [15,10], [15,10]], 'workout': 3, 'position': 2},
#             1: {'stats': [[10,15], [ 8,15], [12,10]], 'workout': 8, 'position': 1},
#         }
#     },
#     'EZ_BAR_CURL': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[10,50], [8,50], [8,50]], 'workout': 3, 'position': 3},
#             1: {'stats': [[12,50],[12,50],[12,50],[12,50]], 'workout': 8, 'position': 4},
#         }
#     },
#     'INCLINED_DUMBBELL_BENCH_PRESS': {
#         'area': 'CHEST',
#         'history': {
#             0: {'stats': [[12,60],[12,60],[12,60]], 'workout': 3, 'position': 4},
#         }
#     },
#     'CABLE_CURLS': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[10,30],[10,30],[10,30]], 'workout': 3, 'position': 5},
#         }
#     },
#     'SINGLE_ARM_LAT_PULLDOWN': {
#         'area': 'BACK',
#         'history': {
#             0: {'stats': [[12,70],[12,80],[12,90],[8,90]], 'workout': 4, 'position': 1},
#         }
#     },
#     'T-BAR_ROW': {
#         'area': 'BACK',
#         'history': {
#             0: {'stats': [[8,45],[8,55],[8,57.5]], 'workout': 4, 'position': 3},
#             1: {'stats': [[8,55],[8,60],[8,65]], 'workout': 9, 'position': 1},
#         }
#     },
#     'DUMBBELL_LATERAL_RAISE': {
#         'area': 'ARMS',
#         'history': {
#             0: {'stats': [[12,20],[12,20]], 'workout': 4, 'position': 5},
#             1: {'stats': [[12,20],[12,20]], 'workout': 9, 'position': 5},
#         }
#     },
#     'CABLE_FACE_PULL': {
#         'area': 'BACK',
#         'history': {
#             0: {'stats': [[12,50],[12,50]], 'workout': 4, 'position': 6},
#         }
#     },
#     "LEG_PRESS": {
#         'area': "LEGS",
#         'history': {
#             0: {'stats': [[10,180],[10,200],[10,200]], 'workout': 5, 'position': 3},
#             1: {'stats': [[12,90],[12,140],[12,180],[12,190]],'workout': 6, 'position': 1},
#         }
#     },
#     'SEATED_CALF_EXTENSION': {
#         'area': "LEGS",
#         'history': {
#             0: {'stats': [[15,135],[15,130],[15,135]], 'workout': 5, 'position': 4},
#             1: {'stats': [[12,135],[12,135]], 'workout': 6, 'position': 6},
#         }
#     },
#     'HIP_ABDUCTION': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[12,220],[12,220],[12,225]], 'workout': 5, 'position': 5},
#         }
#     },
#     "SEATED_LEG_PRESS": {
#         'area': "LEGS",
#         'history': {
#             0: {'stats': [[10,205],[12,210]], 'workout': 5, 'position': 6},
#         }
#     },
#     'HIP_ADDUCTION': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[12,180],[15,190],[15,205]], 'workout': 6, 'position': 5},
#         }
#     },
#     'INCLINED_CHEST_PRESS': {
#         'area': 'CHEST',
#         'history': {
#             0: {'stats': [[10,85],[10,75],[10,65]], 'workout': 7, 'position': 2},
#             1: {'stats': [[12,75],[8,75],[10,75]], 'workout': 8, 'position': 2},
#         }
#     },
#     'CHEST_PRESS': {
#         'area': 'CHEST',
#         'history': {
#             0: {'stats': [[10,75],[5,75],[5,65],[6,65],[4,55]], 'workout': 7, 'position': 3},
#         }
#     },
#     'CHEST_PRESS_MACHINE': {
#         'area': 'CHEST',
#         'history': {
#             0: {'stats': [[12,30],[12,20],[12,10]], 'workout': 7, 'position': 4}
#         }
#     },
#     'PECTORAL_FLY': {
#         'area': 'CHEST',
#         'history': {
#             0: {'stats': [[12,25],[12,25],[12,25],[12,30]], 'workout': 7, 'position': 5},
#             1: {'stats': [[12,70],[12,70],[12,70]], 'workout': 8, 'position': 3},
#         }
#     },
#     'COMPOUND_ROW_MACHINE': {
#         'area': 'BACK',
#         'variation_note': 'Iteration(s) [0] were done using the variation in which the palms are facing upwards at a 45-degree angle, and the subject pulls towards the waist',
#         'history': {
#             0: {'stats': [[15,100],[12,110],[12,105]], 'workout': 9, 'position': 6},
#         }
#     },
#     'HACK_SQUAT': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[12,50],[12,90],[12,140]], 'workout': 10, 'position': 2},
#         }
#     },
#     'SEATED_CALF_RAISE': {
#         'area': 'LEGS',
#         'history': {
#             0: {'stats': [[15,30],[15,30],[15,30]], 'workout': 10, 'position': 3},
#         }
#     }
# }
# def exercise_history_to_csv():
#     df_output = pd.DataFrame()
#     for EXERCISE,data in exercise_history.items():
#         units = data.get('units','')
#         area = data['area']
#         for instance,data2 in data['history'].items():
#             for set_index, set in enumerate(data2['stats']):
#                 df_tmp = pd.DataFrame({'exercise': [EXERCISE], 'area': [area], 'instance': [instance], 'workout': [data2['workout']], 'position': [data2['position']], 'set': [set_index], 'units': [units], 'data': [set_to_string(set,units)]})
#                 df_output = pd.concat([df_output,df_tmp])
#     return df_output.sort_values(by=PRIMARY_KEYS).reset_index(drop=True)

    


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        # wsl python3 Fitness/exercises.py WORKOUT
        if sys.argv[-1].upper().strip() == 'WORKOUT':
            HISTORY = EXERCISE_HISTORY_CLS(EXERCISE_HISTORY_PATH)
            HISTORY.add_workout()
        # wsl python3 Fitness/exercises.py SUMMARY | clip.exe
        elif sys.argv[-1].upper().strip() == 'SUMMARY':
            HISTORY = EXERCISE_HISTORY_CLS(EXERCISE_HISTORY_PATH)
            HISTORY.print_exercise_history_summary()
