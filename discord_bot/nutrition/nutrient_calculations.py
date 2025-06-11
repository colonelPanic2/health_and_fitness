def percent_fat(fat_grams, calories):
    return round((fat_grams * 9) / calories * 100, 3)
def percent_carbs(carbs_grams, calories):
    return round((carbs_grams * 4) / calories * 100, 3)
def percent_protein(protein_grams, calories):
    return round((protein_grams * 4) / calories * 100, 3)
def ci_lean_gain(body_weight):
    # Return the range of daily calorie intake recommended for lean gaining
    values = [round(16*body_weight), round(18*body_weight)]
    average = round(17*body_weight)
    print(f'Calories:\n\tMIN: {values[0]}\n\tAVG: {average}\n\tMAX: {values[1]}')
    return average

CURRENT_BODY_WEIGHT = 159.4#int(input('Current body weight (lbs): '))

calorie_intake_avg = ci_lean_gain(CURRENT_BODY_WEIGHT)

calories = calorie_intake_avg
protein_grams = 231
net_carbs_grams = 224#+38 # 38 grams of fiber
fat_grams_map = {
    'fat': {
        'grams': 88,
        'percent': '',
    },
    'saturated': {
        'grams': 27,
        'percent': '',
    },
    'polyunsaturated': {
        'grams': 12,
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

