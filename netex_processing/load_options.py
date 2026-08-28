import os
import pandas as pd


def load_options(folder):
    options = {}

    # Code that applies to the workflow at the province of Gelderland
    if os.path.exists(f'{folder}/abc-lijnen.xlsx'):
        print(f'Inladen ABC-categorieën')
        options['linecode_categories'] = pd.read_excel(f'{folder}/abc-lijnen.xlsx', sheet_name='data').replace(float('nan'), None).set_index('code')["ABC-Category"].to_dict()

    return options