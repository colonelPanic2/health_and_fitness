def percent_fat(fat_grams, calories):
    return round((fat_grams * 9) / calories * 100, 3)
def percent_carbs(carbs_grams, calories):
    return round((carbs_grams * 4) / calories * 100, 3)
def percent_protein(protein_grams, calories):
    return round((protein_grams * 4) / calories * 100, 3)


calories = 2487
protein_grams = 214
net_carbs_grams = 211#+38 # 38 grams of fiber
fat_grams_map = {
    'fat': {
        'grams': 82,
        'percent': '',
    },
    'saturated': {
        'grams': 24,
        'percent': '',
    },
    'polyunsaturated': {
        'grams': 11,
        'percent': ''
    },
    'monounsaturated': {
        'grams': 23,
        'percent': ''
    }
}

protein_percent = percent_protein(protein_grams, calories)
net_carbs_percent=percent_carbs(net_carbs_grams, calories)
for key in fat_grams_map.keys():
    fat_grams_map[key]['percent'] = percent_fat(fat_grams_map[key]['grams'],calories)

print(f'''Protein  : {protein_percent}%\nNet Carbs: {net_carbs_percent}%''')
print('\n    '.join([f'{key}: {data["percent"]}%' for key,data in fat_grams_map.items()]))
print(f'Total: {protein_percent+net_carbs_percent+fat_grams_map['fat']['percent']}%')
