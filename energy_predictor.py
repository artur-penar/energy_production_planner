import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Wczytaj dane z pliku Excel
df = pd.read_excel("data.xlsx")  # podaj właściwą nazwę pliku

df.columns = df.columns.str.strip()  # USUWA SPACJE z nazw kolumn

print(df.columns.tolist())  # Wyświetli dokładne nazwy kolumn
# Przekształć datę na datetime, jeśli trzeba
df["data"] = pd.to_datetime(df["data"], format="%d.%m.%Y")

# Zamień kolumnę 'data' na samą datę (bez godziny)
df["data"] = df["data"].dt.date

# Wybierz cechy wejściowe
features = ["temp", "gti", "godzina", "is_holiday"]
targets = ["rco 243 kW", "rco 894 kW", "energia_oddana_kWh"]


# Przykład: przewidujemy tylko tam, gdzie brakuje wartości (np. NaN)
for target in targets:
    # Podziel na dane z targetem i bez
    train_df = df[df[target].notna()]
    predict_df = df[df[target].isna()]
    if len(predict_df) == 0:
        continue  # nic do przewidzenia

    X_train = train_df[features]
    y_train = train_df[target]
    X_pred = predict_df[features]

    # Trenuj model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Przewiduj brakujące wartości
    y_pred = model.predict(X_pred)
    df.loc[df[target].isna(), target] = y_pred

# Zapisz uzupełnione dane również do Excela
df.to_excel("uzupelnione_dane.xlsx", index=False)
print("Przewidywanie zakończone. Wynik zapisano do uzupelnione_dane.xlsx")

# Przygotuj tabelę przestawną dla rco 243 kW
pivot_243 = df.pivot_table(
    index="godzina", columns="data", values="rco 243 kW", aggfunc="sum"
)
pivot_243.index = pivot_243.index + 1  # godziny od 1 do 24
pivot_243.index.name = "godzina"

# Przygotuj tabelę przestawną dla rco 894 kW
pivot_894 = df.pivot_table(
    index="godzina", columns="data", values="rco 894 kW", aggfunc="sum"
)
pivot_894.index = pivot_894.index + 1
pivot_894.index.name = "godzina"

pivot_energia_oddana = df.pivot_table(
    index="godzina", columns="data", values="energia_oddana_kWh", aggfunc="sum"
)
pivot_energia_oddana.index = pivot_energia_oddana.index + 1
pivot_energia_oddana.index.name = "godzina"

# Zapisz do plików Excel
pivot_243.to_excel("energia_rco_243_v2.xlsx", float_format="%.2f")
pivot_894.to_excel("energia_rco_894_v2.xlsx", float_format="%.2f")
pivot_energia_oddana.to_excel("energia_oddana_v2.xlsx", float_format="%.2f")
print("Dane zapisane do energia_rco_243.xlsx oraz energia_rco_894.xlsx")
