import sys, os
import re
import pandas as pd

SCHEDULE_RELATIVE_PATH = 'data/exercise_logs/schedule'#/schedule_history.csv'
SCHEDULE_HISTORY_PATH = str('C:/Files/Fitness/' if sys.platform.startswith('win') else '/home/luis/Documents/Fitness/') + SCHEDULE_RELATIVE_PATH
SCHEDULE_HISTORY_PRIMARY_KEYS = ['schedule', 'exercise', 'position', 'area', 'units', 'description']
EXERCISES_PRIMARY_KEYS = ['exercise','area','units','requirement','description']
def print_list(inp_list,title=''):
    if title != '':
        title = title+': \n'
    print(title + '\t' + '\n\t'.join([f"""({' '*(len(str(len(inp_list)))-len(str(i+1)))}{i+1} / {len(inp_list)}) {element}""" for i,element in enumerate(inp_list)]))
def process_exercise_name( exercise_name):
    return re.sub(r'__+','_',str(exercise_name).strip().upper().replace(' ','_')).strip('_')

class SCHEDULE_HISTORY_CLS():
    def __init__(self,PATH):
        self.schedule_history_path = f'{PATH}/schedule_history.csv'
        self.exercises_path = f'{PATH}/exercises.csv'
        self.creating_schedule = False
        self.current_day = None
        self.current_exercise = None
        self.current_exercise_position = None
        self.schedule = None
        self.refresh_data()
    def refresh_data(self):
        # Create directory and file if they don't exist
        if not os.path.exists(self.schedule_history_path):
            self.schedule_data = pd.DataFrame(columns=SCHEDULE_HISTORY_PRIMARY_KEYS+['dw_mod_ts'])
        else:
            self.schedule_data = pd.read_csv(self.schedule_history_path, keep_default_na=False)
        if not os.path.exists(self.exercises_path):
            self.exercise_data = pd.DataFrame(columns=EXERCISES_PRIMARY_KEYS+['dw_mod_ts'])
        else:
            self.exercise_data = pd.read_csv(self.schedule_history_path, keep_default_na=False)
        # self.most_recent_week = self.data['week'].max() if not self.data.empty else None
        if not self.exercise_data.empty:
            self.exercises = self.exercise_data['exercise'].unique().tolist()
            self.areas = self.exercise_data['areas'].unique().tolist()
            self.units = self.exercise_data['units'].unique().tolist()
        else:
            self.exercises, self.areas, self.units = [], [], []
    def get_most_recent_schedule(self):
        if self.schedule_data.empty:
            return -1
        return self.schedule_data['schedule'].max()
    def create_schedule(self):
        self.creating_schedule = True
        self.current_day = 0
        self.current_exercise_position = 0
        self.new_schedule = self.get_most_recent_schedule() + 1
        self.schedule = pd.DataFrame(columns=SCHEDULE_HISTORY_PRIMARY_KEYS)
    def add_exercise(self, exercise):
        if self.exercise_exists(exercise['name']):
            self.exercise_data['requirement'] = self.exercise_data.apply(lambda x: x['requirement'] if x['exercise'] == exercise['name'] else exercise['requirement'], axis=1)
        df_new_exercise = pd.DataFrame({'exercise': [exercise['name']], 'area': [exercise['area']], 'units': [exercise['units']], 'requirement': [exercise['requirement']], 'description': [exercise['description']]})
    def add_day(self, day_plan):
        pass
    def add_schedule(self):
        pass
    def exercise_exists(self,exercise_name):
        return exercise_name in self.exercises