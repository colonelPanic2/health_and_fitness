import sys, os
import pandas as pd

SCHEDULE_RELATIVE_PATH = 'data/exercise_logs/schedule_history.csv'
SCHEDULE_HISTORY_PATH = str('C:/Files/Fitness/' if sys.platform.startswith('win') else '/home/luis/Documents/Fitness/') + SCHEDULE_RELATIVE_PATH
PRIMARY_KEYS = ['week', 'schedule', 'position', 'exercise', 'area', 'units', 'description']
def print_list(inp_list,title=''):
    if title != '':
        title = title+': \n'
    print(title + '\t' + '\n\t'.join([f"""({' '*(len(str(len(inp_list)))-len(str(i+1)))}{i+1} / {len(inp_list)}) {element}""" for i,element in enumerate(inp_list)]))

class SCHEDULE_HISTORY_CLS():
    def __init__(self,PATH):
        self.path = PATH
        self.primary_keys = PRIMARY_KEYS
        self.refresh_data()
    def refresh_data(self):
        # Create directory and file if they don't exist
        if not os.path.exists(self.path):
            self.data = pd.DataFrame(columns=self.primary_keys+['dw_mod_ts'])
        else:
            self.data = pd.read_csv(self.path, keep_default_na=False)
        self.most_recent_week = self.data['week'].max() if not self.data.empty else None
        self.exercises = self.data['exercise'].unique().tolist() if not self.data.empty else []