import matplotlib.pyplot as plt
from datetime import datetime
import calendar
import numpy as np

# Dane sezonów
seasons = [
    ("2007/2008", "2007-09-21", "2008-04-28"),
    ("2008/2009", "2008-09-17", "2009-04-21"),
    ("2009/2010", "2009-10-02", "2010-04-29"),
    ("2010/2011", "2010-09-29", "2011-04-28"),
    ("2011/2012", "2011-10-11", "2012-04-26"),
    ("2012/2013", "2012-10-08", "2013-04-24"),
    ("2013/2014", "2013-09-24", "2014-04-23"),
    ("2014/2015", "2014-10-03", "2015-05-05"),
    ("2015/2016", "2015-09-30", "2016-05-04"),
    ("2016/2017", "2016-09-23", "2017-05-15"),
    ("2017/2018", "2017-09-27", "2018-04-09"),
    ("2018/2019", "2018-09-25", "2019-05-17"),
    ("2019/2020", "2019-09-24", "2020-05-19"),
    ("2020/2021", "2020-09-30", "2021-05-19"),
    ("2021/2022", "2021-09-21", "2022-05-05"),
    ("2022/2023", "2022-09-22", "2023-05-16"),
    ("2023/2024", "2023-10-10", "2024-05-13"),
    ("2024/2025", "2024-09-30", "2025-05-30")
]

season_labels = [s[0] for s in seasons]
start_dates = [datetime.strptime(s[1], "%Y-%m-%d") for s in seasons]
end_dates = [datetime.strptime(s[2], "%Y-%m-%d") for s in seasons]

def get_day_of_year(date):
    return date.timetuple().tm_yday

def get_sep1_day_of_year(year):
    return datetime(year, 9, 1).timetuple().tm_yday

start_positions = []
durations = []

for start, end in zip(start_dates, end_dates):
    sep1 = get_sep1_day_of_year(start.year)
    start_day = get_day_of_year(start)
    if start.month >= 9:
        start_pos = start_day - sep1
    else:
        days_in_year = 366 if calendar.isleap(start.year) else 365
        start_pos = start_day + (days_in_year - sep1)

    # Koniec sezonu
    if end.year == start.year:
        end_sep1 = sep1
    else:
        end_sep1 = get_sep1_day_of_year(end.year)
    end_day = get_day_of_year(end)
    if end.month >= 9:
        end_pos = end_day - end_sep1
    else:
        days_in_year = 366 if calendar.isleap(end.year) else 365
        end_pos = end_day + (days_in_year - end_sep1)

    duration = end_pos - start_pos
    if duration < 0:
        duration += 366 if calendar.isleap(start.year) else 365

    start_positions.append(start_pos)
    durations.append(duration)

# Przygotuj kolory dla każdego słupka (np. colormap)
cmap = plt.get_cmap('tab20')
colors = [cmap(i % 20) for i in range(len(seasons))]

# Tworzenie wykresu
fig, ax = plt.subplots(figsize=(12, 8))

y = range(len(seasons))
bars = ax.barh(y, durations, left=start_positions, color="#1f77b4", edgecolor='black')  # standardowy niebieski

# Dodaj ilość dni sezonu na każdym słupku, wyśrodkowane względem osi X całego wykresu
center_x = ax.get_xlim()[1] / 2  # środek osi X
for i, duration in enumerate(durations):
    ypos = i
    ax.text(center_x, ypos, str(duration), ha='center', va='center', color='white',
            fontsize=16, fontweight='bold')  # usunięto bbox

ax.set_yticks(y)
ax.set_yticklabels(season_labels)
ax.set_ylabel("Sezon")

# Oś X: od września do 1 lipca (8 miesięcy, ok. 283 dni)
ax.set_xlim(0, 283)  # 0 = 1 września, 283 = 11 czerwca (28 dekad po 10 dni)

# Etykiety co 10 dni od 1 września do 11 czerwca
xticks = list(range(0, 284, 10))  # 0, 10, ..., 280
xticklabels = []
months = [
    "Wrz", "Paź", "Lis", "Gru", "Sty", "Lut", "Mar", "Kwi", "Maj", "Cze"
]
month_starts = [0, 30, 61, 92, 122, 153, 181, 212, 242, 273]

for tick in xticks:
    for i, start in enumerate(month_starts):
        if i == len(month_starts) - 1 or tick < month_starts[i + 1]:
            day = tick - start + 1
            if day > 0 and day <= 31:
                label = f"{day} {months[i]}"
            else:
                label = ""
            break
    xticklabels.append(label)

ax.set_xticks(xticks)
ax.set_xticklabels(xticklabels, rotation=45)

ax.set_title("Czas trwania sezonów grzewczych (od rozpoczęcia do zakończenia) – oś od 1 września do 11 czerwca")
plt.tight_layout()
plt.savefig("wykres_sezonow_grzewczych_wrzesien_czerwiec.png", dpi=300, bbox_inches="tight")
plt.show()