import csv
import random
from itertools import combinations

#Эта штука генерирует списки что бы вручную не пришлось

OPs = ['PM', 'IVT', 'ITSS', 'IB'] #Названия направлений
Days = ['01.08', '02.08', '03.08', '04.08'] #дни

#Количество всех абитуриентов
total_counts = {
    '01.08': {'PM': 60, 'IVT': 100, 'ITSS': 50, 'IB': 70},
    '02.08': {'PM': 380, 'IVT': 370, 'ITSS': 350, 'IB': 260},
    '03.08': {'PM': 1000, 'IVT': 1150, 'ITSS': 1050, 'IB': 800},
    '04.08': {'PM': 1240, 'IVT': 1390, 'ITSS': 1240, 'IB': 1190}
}

#количество пересечений для множества абитуриентов только для двух ОП
pair_data = {
    '01.08': {('PM', 'IVT'): 22, ('PM', 'ITSS'): 17, ('PM', 'IB'): 20, ('IVT', 'ITSS'): 19, ('IVT', 'IB'): 22, ('ITSS', 'IB'): 17},
    '02.08': {('PM', 'IVT'): 190, ('PM', 'ITSS'): 190, ('PM', 'IB'): 150, ('IVT', 'ITSS'): 190, ('IVT', 'IB'): 140, ('ITSS', 'IB'): 120},
    '03.08': {('PM', 'IVT'): 760, ('PM', 'ITSS'): 600, ('PM', 'IB'): 470, ('IVT', 'ITSS'): 750, ('IVT', 'IB'): 460, ('ITSS', 'IB'): 500},
    '04.08': {('PM', 'IVT'): 1090, ('PM', 'ITSS'): 1110, ('PM', 'IB'): 1070, ('IVT', 'ITSS'): 1050, ('IVT', 'IB'): 1040, ('ITSS', 'IB'): 1090}
}

#Количество для трех абитуриентов
triple_data = {
    '01.08': {('PM', 'IVT', 'ITSS'): 5, ('PM', 'IVT', 'IB'): 5, ('PM', 'ITSS', 'IB'): 5, ('IVT', 'ITSS', 'IB'): 5},
    '02.08': {('PM', 'IVT', 'ITSS'): 70, ('PM', 'IVT', 'IB'): 70, ('PM', 'ITSS', 'IB'): 70, ('IVT', 'ITSS', 'IB'): 50},
    '03.08': {('PM', 'IVT', 'ITSS'): 500, ('PM', 'IVT', 'IB'): 260, ('PM', 'ITSS', 'IB'): 300, ('IVT', 'ITSS', 'IB'): 250},
    '04.08': {('PM', 'IVT', 'ITSS'): 1020, ('PM', 'IVT', 'IB'): 1020, ('PM', 'ITSS', 'IB'): 1000, ('IVT', 'ITSS', 'IB'): 1040}
}
#Идиоты которые подали завления сразу на 4 направления
quad_data = {
    '01.08': 3,
    '02.08': 50,
    '03.08': 200,
    '04.08': 1000
}


for day in Days:
    given = {}
    for pair, count in pair_data[day].items():
        given[frozenset(pair)] = count
    for triple, count in triple_data[day].items():
        given[frozenset(triple)] = count
    given[frozenset(OPs)] = quad_data[day]

    # Compute exact counts
    all_subsets = []
    for r in range(len(OPs) + 1):
        for subset in combinations(OPs, r):
            all_subsets.append(frozenset(subset))

    exact = {}
    for S in all_subsets:
        count = 0
        for T, val in given.items():
            if S.issubset(T):
                count += (-1) ** (len(T) - len(S)) * val
        exact[S] = count

    # Generate entrants
    entrants = []
    entrant_id = 1
    for S, num in exact.items():
        if num <= 0:
            continue
        op_list = list(S)
        for _ in range(num):
            phys = random.randint(0, 100)
            rus = random.randint(0, 100)
            math = random.randint(0, 100)
            ind = random.randint(0, 10)
            total = phys + rus + math + ind
            consent = random.choice([True, False])
            priorities = random.sample(range(1, len(op_list) + 1), len(op_list))
            entrant = {
                'id': entrant_id,
                'Согласие': consent,
                'Физика/ИКТ': phys,
                'Русский язык': rus,
                'Математика': math,
                'ИД': ind,
                'Всего': total,
                'Приоритет': {op: pri for op, pri in zip(op_list, priorities)}
            }
            entrants.append(entrant)
            entrant_id += 1

    # For day 04.08, ensure enough consents
    if day == '04.08':
        spots = {'PM': 40, 'IVT': 50, 'ITSS': 30, 'IB': 20}
        for op in OPs:
            consented = [e for e in entrants if op in e['Приоритет'] and e['Согласие']]
            if len(consented) <= spots[op]:
                # Make more True
                non_consented = [e for e in entrants if op in e['Приоритет'] and not e['Согласие']]
                num_to_change = spots[op] + 1 - len(consented)
                if num_to_change > 0 and non_consented:
                    to_change = random.sample(non_consented, min(num_to_change, len(non_consented)))
                    for e in to_change:
                        e['Согласие'] = True

    # Write CSVs
    for op in OPs:
        filename = f'{day}_{op}.csv'
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['ID', 'Согласие', 'Приоритет', 'Физика/ИКТ', 'Русский язык', 'Математика', 'ИД', 'Всего']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for entrant in entrants:
                if op in entrant['Приоритет']:
                    writer.writerow({
                        'ID': entrant['id'],
                        'Согласие': entrant['Согласие'],
                        'Приоритет': entrant['Приоритет'][op],
                        'Физика/ИКТ': entrant['Физика/ИКТ'],
                        'Русский язык': entrant['Русский язык'],
                        'Математика': entrant['Математика'],
                        'ИД': entrant['ИД'],
                        'Всего': entrant['Всего']
                    })