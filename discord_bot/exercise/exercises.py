import pandas as pd
import json
import sys, os
import re
from tabulate import tabulate
import matplotlib.pyplot as plt
import io
from discord import File
import zipfile

EXERCISE_RELATIVE_PATH = 'data/exercise_logs/exercise_history.csv'
EXERCISE_HISTORY_PATH = str('C:/Files/Fitness/' if sys.platform.startswith('win') else '/home/luis/Documents/Fitness/') + EXERCISE_RELATIVE_PATH
PRIMARY_KEYS = ['exercise','area','instance','workout','position','set']


def render_table_image(df: pd.DataFrame) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(len(df.columns) * 2, len(df) * 0.5 + 1))
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    table.scale(1, 1.5)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)  # Close the figure to prevent memory leaks
    return buffer
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
    ### <N_REPS>x<N_POUNDS>
    sets_x_weights_pattern = r'(\d+x\d+(\.\d+){1})'
    sets_x_weights_match = bool(units == '' and re.match(rf'^{sets_x_weights_pattern}$',set_entry))
    ### <N_REPS>
    sets_pattern = r'(\d+)'
    sets_match = bool(units != '' and re.match(rf'^{sets_pattern}$',set_entry))
    ### <N_REPS>x<N_POUNDS>;<N_REPS>x<N_POUNDS>
    supersets_x_weights_pattern = rf'^{sets_x_weights_pattern};{sets_x_weights_pattern}$'
    supersets_x_weights_match = bool( units == '' and re.match(supersets_x_weights_pattern,set_entry))
    ### <N_REPS>;<N_REPS>
    supersets_pattern = rf'^{sets_pattern};{sets_pattern}$'
    supersets_match = bool( units != '' and re.match(supersets_pattern,set_entry))
    ### Any of the above patterns match
    return bool( sets_x_weights_match or sets_match or supersets_x_weights_match or supersets_match )
def process_exercise_name( exercise_name):
    return re.sub(r'__+','_',str(exercise_name).strip().upper().replace(' ','_')).strip('_')
# SW-LT : Shoulder_width-legs_together, each variation gets 1/2 the reps

class EXERCISE_HISTORY_CLS():
    def __init__(self,PATH):
        self.path = PATH
        self.primary_keys = PRIMARY_KEYS
        self.refresh_data()
    def partition_data(self):
        self.data_partition = {exercise: self.data.query('exercise == @exercise') for exercise in self.exercises}
    def refresh_data(self):
        if not os.path.exists(self.path):
            self.data = pd.DataFrame(['exercise','area','instance','workout','position','set','data','units','dw_mod_ts'])
        else:
            self.data = pd.read_csv(self.path,keep_default_na=False)
        if 'instance' in self.data.columns:
            self.data['instance'] = pd.to_numeric(self.data['instance'], errors='coerce').fillna(-1).astype(int)
        self.exercises = sorted(list(set(self.data['exercise'].tolist())))
        self.partition_data()
        self.areas = list(set(self.data['area'].tolist()))
        self.units = list(set(self.data[self.data['units'].apply(lambda x: pd.notna(x) and str(x).strip()!='')]['units'].tolist()))
        self.workouts = list(set(self.data['workout'].tolist()))
        self.get_latest_workout()
        self.new_exercises = {}
    ### NOTE: Functions for getting data from the dataset
    def get_units(self, exercise):
        if not self.exercise_exists(exercise):
            return self.new_exercises.get(exercise,{}).get('units')#None
        units = self.data_partition.get(exercise,pd.DataFrame(columns=['units']))['units']#.tolist()
        if units.empty:
            return None
        units = units.tolist()[0]
        if pd.isna(units) or str(units).strip() == '':
            return ''
        else:
            return units
    def get_area(self, exercise):
        if not self.exercise_exists(exercise):
            return self.new_exercises.get(exercise,{}).get('area')#None
        area = self.data_partition.get(exercise,pd.DataFrame(columns=['area']))['area']#.tolist()
        if area.empty:
            return None
        area = area.tolist()[0]
        return area
    def get_latest_instance(self, exercise):
        if not self.exercise_exists(exercise):
            return -1
        instance = self.data_partition.get(exercise,pd.DataFrame(columns=['instance']))['instance'].max()
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
            df_tmp = self.data_partition.get(EXERCISE,pd.DataFrame(columns=self.primary_keys)).sort_values(by=self.primary_keys)
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

instance_data_cols = ['exercise','instance','position','set','data']
class ExerciseTracker(EXERCISE_HISTORY_CLS):
    def __init__(self, PATH):
        super().__init__(PATH)
        self.log_workout = False
        self.workout_exercise_position = None
        self.current_exercise = None
        self.cache_current_exercise = None
        self.new_workout = None
        self.workout = None
        self.updating_sets = False
        # Variables for modifying source data
        self.selected_exercise = None # {"name": "<EXERCISE_NAME>", "mode": "RENAME"}
        self.partition_data()
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
        # Variables for logging workouts
        self.log_workout = True
        self.workout_exercise_position = 0
        self.cache_current_exercise = None
        self.current_exercise = None
        self.updating_sets = False
        self.new_workout = self.get_latest_workout() + 1
        self.workout = {}
        return f'Started logging new workout: {self.new_workout}'
    def select_exercise(self, exercise_name, select_mode=None):
        exercise_name = process_exercise_name(exercise_name)
        if not self.exercise_exists(exercise_name):
            return f'''ERROR: Exercise, "{exercise_name}", doesn\'t exist'''
        self.selected_exercise = {"name": exercise_name, "area": self.get_area(exercise_name), "mode": select_mode}
        return f'''({select_mode}) Selected "{exercise_name}"'''
    def show_selected(self):
        if self.selected_exercise is None:
            return f'No exercises have been selected yet. Run "/select_exercise_*" to select an exercise for a specific purpose'
        return f'MODE: "{self.selected_exercise["mode"]}\nNAME: "{self.selected_exercise["name"]}"\nAREA: "{self.selected_exercise["area"]}"'
    def rename_exercise(self, exercise):
        if self.selected_exercise is None or self.selected_exercise.get('mode','') != "RENAME":
            return f'No exercise selected for renaming. Choose an exercise with "/select_exercise_rename"'
        selected_name, selected_area = self.selected_exercise['name'], self.selected_exercise['area']
        name = exercise['exercise_name']
        area = exercise['area'] if exercise['area'] != '' else selected_area
        self.data.loc[self.data['exercise'] == selected_name, ['exercise', 'area', 'dw_mod_ts']] = [
            name,
            area,
            pd.Timestamp.now()
        ]
        self.data.to_csv(self.path, index=False)
        self.selected_exercise = None
        self.refresh_data()
        return f'Finished renaming exercise: ("{selected_name}", "{selected_area}") --> ("{name}", "{area}")'
    def get_exercise(self, exercise_name):
        exercise_name = process_exercise_name(exercise_name)#re.sub(r'__+','_',exercise_name.upper().strip().replace(' ','_'))
        if not self.exercise_exists(exercise_name):
            return f"""ERROR: Exercise "{exercise_name}" doesn't exist"""
        if self.workout_exercise_position is None:
            self.workout_exercise_position = 0
        if self.current_exercise is None:
            self.cache_current_exercise = None#self.current_exercise
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
            self.workout_exercise_position = len(self.workout)#+= 1
            self.cache_current_exercise = None#self.current_exercise
            self.current_exercise = None
            self.updating_sets = False
            new_workout = self.new_workout
            msg = self.end_workout()
            return f"Finished logging new workout {new_workout}.\nEnjoy your day off!"
        self.updating_sets = False
        self.cache_current_exercise = None#self.current_exercise
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
        self.workout_exercise_position = len(self.workout)#+= 1
        self.current_exercise = self.cache_current_exercise if self.updating_sets else None
        self.updating_sets = False
        return msg
    def add_new_exercise(self, exercise):
        self.cache_current_exercise = self.current_exercise
        self.current_exercise = exercise['exercise_name']
        if self.cannot_perform_action():
            self.current_exercise = None
            if self.log_workout == False:
                return f'Not currently logging a workout. Run "/start_workout"'
            else:
                return f'UNEXPECTED INPUT DETECTED'
        self.new_exercises[self.current_exercise] = {'units': exercise['units'], 'area': exercise['area']}
        # self.exercises.append(exercise['exercise_name'])
        exercise_log = {'exercise_name': exercise['exercise_name'], 'stats': {i: set_ for i,set_ in enumerate(exercise['sets'])}}
        self.workout[self.workout_exercise_position] = exercise_log
        self.workout_exercise_position = len(self.workout)#+= 1
        self.cache_current_exercise = None#self.current_exercise
        self.current_exercise=None
        self.updating_sets = False
        return f'''Added new exercise:\n"({self.workout_exercise_position}) {exercise['exercise_name']}" - {", ".join(exercise["sets"])}'''
    def get_workout(self):
        # Defined for the definition of "add_workout" in exercises.py
        return self.workout
    def end_workout(self):
        if self.workout is not None and self.workout == {}:
            self.log_workout = False
            self.workout_exercise_position = None
            self.current_exercise = None
            self.cache_current_exercise = None
            self.updating_sets = False
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
        self.cache_current_exercise = None
        self.updating_sets = False
        self.new_workout = None
        self.workout = None
        return msg
    def abort_exercise(self):
        if self.new_workout is None or self.log_workout == False:
            return f'Not currently logging a workout. Run "/start_workout"'
        elif self.current_exercise is None:
            return f'Not currently logging an exercise for workout "{self.new_workout}". Run "/exercise" or "/newexercise"'
        msg = f'ABORT: Stopped logging "{self.current_exercise}" for workout "{self.new_workout}"'
        self.current_exercise = self.cache_current_exercise if self.updating_sets else None
        self.workout_exercise_position = len(self.workout)
        self.cache_current_exercise = None
        self.updating_sets = False
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
        exercise = process_exercise_name(exercise)
        if not self.exercise_exists(exercise):
            return f"""ERROR: Exercise "{exercise}" doesn't exist"""
        latest_instance_index = int(float(self.get_latest_instance(exercise)))
        top_3_range = list(range(max(0,latest_instance_index-2),latest_instance_index+1))
        # Format the DataFrame as a code block for Discord
        df = self.data_partition.get(exercise,pd.DataFrame(instance_data_cols)).query('instance in @top_3_range')[instance_data_cols]
        if df.empty:
            return "No data found for this exercise."
        # Convert DataFrame to string with tabulate for better formatting
        try:
            # table = tabulate(df, headers='keys', tablefmt='github', showindex=False)
            table = File(fp=render_table_image(df), filename=f'{exercise}.png')
            return table
        except ImportError:
            table = df.to_string(index=False)
            return f"```\n{table}\n```"
    def _reset_state(self):
        try:
            ### Reset the ExerciseTracker attributes to their default states
            self.log_workout = False
            self.workout_exercise_position = None
            self.current_exercise = None
            self.cache_current_exercise = None
            self.updating_sets = False
            self.new_workout = None
            self.workout = None
            self.selected_exercise = None
            ### Reset the EXERCISE_HISTORY_CLS attributes to their default states
            self.refresh_data()
            return f'Bot state restored successfully'
        except Exception as e:
            return f"FATAL ERROR: COULDN'T RESTORE THE BOT TO IT'S DEFAULT STATE."
    def _get_backup(self):
        csv_buffer = io.StringIO()
        self.data = pd.read_csv(self.path,keep_default_na=False)
        self.data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(self.path.split('/')[-1].replace('.csv','_bckp.csv'), csv_buffer.read())
        zip_buffer.seek(0)
        return zip_buffer
    def change_sets(self, index_and_exercise):
        parse_input = re.findall(r'^(\d+) - (\S+)$', index_and_exercise)
        if len(parse_input) == 0:
            return f'ERROR: Invalid input, "{index_and_exercise}" ({parse_input})'
        exercise_index, exercise = int(parse_input[0][0]), process_exercise_name(parse_input[0][1])
        actual_name = self.workout.get(exercise_index,{'exercise_name': ""}).get('exercise_name',"")
        if len(self.workout) > 0 and not (0<= exercise_index < len(self.workout)):
            return f'ERROR: exercise index "{exercise_index}" out of range for workout of size {len(self.workout)}'
        elif actual_name == "":
            return f'''ERROR: Couldn't retrieve exercise name for index "{exercise_index}"'''
        elif actual_name != exercise:
            return f'''ERROR: the exercise, "{actual_name}", at index "{exercise_index}" doesn't match the given exercise, "{exercise}"'''
        self.cache_current_exercise = self.cache_current_exercise if self.updating_sets else self.current_exercise
        self.current_exercise = exercise
        self.workout_exercise_position = exercise_index
        self.updating_sets = True
        old_sets = ", ".join([self.workout[self.workout_exercise_position]['stats'][i] for i in range(len(self.workout[self.workout_exercise_position]['stats']))])
        return f'Modifying sets for exercise "{exercise_index} - {exercise}"\nOld sets: {old_sets}'
    # Merge the data from name1 and name2 into name2 (only meant for the same exercise with different names)
    def merge_name1_into_name2(self, name1, name2):
        name1, name2 = process_exercise_name(name1), process_exercise_name(name2)
        df_empty = pd.DataFrame(columns=self.primary_keys+['data','units','dw_mod_ts'])
        df_name1 = self.data_partition.get(name1,df_empty)
        df_name2 = self.data_partition.get(name2,df_empty)
        if df_name1.empty:
            return f'ERROR: No data found for exercise, "{name1}"'
        if df_name2.empty:
            return f'ERROR: No data found for exercise, "{name2}"'
        units_name1 = df_name1['units'].drop_duplicates().tolist()[0]
        units_name2 = df_name2['units'].drop_duplicates().tolist()[0]
        if units_name1 != units_name2:
            return f'ERROR: Cannot merge exercises with different units ("{units_name1}" != "{units_name2}")'
        # Combine the dataframes
        df_combined = pd.concat([df_name1, df_name2]).reset_index(drop=True)
        # Assign new instance numbers by group (workout, position)
        df_combined['instance'] = df_combined.sort_values(by=['workout', 'position']).groupby(['workout', 'position'], sort=False).ngroup()
        df_combined['exercise'] = name2
        self.refresh_data()
        return f'Successfully merged all data from "{name1}" into "{name2}"'
    


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
