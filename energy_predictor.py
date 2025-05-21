import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Wczytaj dane z pliku Excel
df = pd.read_excel("learning_data_reduced.xlsx")  # podaj właściwą nazwę pliku

df.columns = df.columns.str.strip()  # USUWA SPACJE z nazw kolumn

print(df.columns.tolist())
# Przekształć datę na datetime, jeśli trzeba
df["data"] = pd.to_datetime(df["data"], format="%d.%m.%Y")

# Zamień kolumnę 'data' na samą datę (bez godziny)
df["data"] = df["data"].dt.date

# Wybierz cechy wejściowe
features = ["temp", "gti", "godzina", "is_holiday"]
targets = ["rco 243 kW", "energia_oddana_kWh"]


# Przykład: przewidujemy tylko tam, gdzie brakuje wartości (np. NaN)
for target in targets:
    train_df = df[df[target].notna()]
    X_train = train_df[features]
    y_train = train_df[target]

    # Podział na zbiór treningowy i testowy
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42
    )
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_tr, y_tr)
    y_pred_test = model.predict(X_te)

    mae = mean_absolute_error(y_te, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
    r2 = r2_score(y_te, y_pred_test)
    print(f"{target}: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.2f}")
    print(f"Liczba próbek do treningu/testu dla {target}: {len(train_df)}")

    # Predykcja tylko jeśli są braki
    predict_df = df[df[target].isna()]
    if len(predict_df) > 0:
        X_pred = predict_df[features]
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


pivot_energia_oddana = df.pivot_table(
    index="godzina", columns="data", values="energia_oddana_kWh", aggfunc="sum"
)
pivot_energia_oddana.index = pivot_energia_oddana.index + 1
pivot_energia_oddana.index.name = "godzina"

# Zapisz do plików Excel
pivot_243.to_excel("energia_rco_243.xlsx", float_format="%.2f")
pivot_energia_oddana.to_excel("energia_oddana.xlsx", float_format="%.2f")
print("Dane zapisane do energia_rco_243.xlsx oraz energia_rco_894.xlsx")
