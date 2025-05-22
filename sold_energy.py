import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Wczytaj dane z przewidywaną produkcją PV
df = pd.read_excel("data/input/pv_predicted.xlsx")
df.columns = df.columns.str.strip()

print(df.columns.tolist())
df["date"] = pd.to_datetime(df["date"], errors="coerce")
if df["date"].dtype != "O":
    df["date"] = df["date"].dt.date

# Wybierz cechy: produkcja PV, godzina, święto
features_oddana = ["produced_energy", "hour", "is_holiday"]
target_oddana = "sold_energy"

train_df = df[df[target_oddana].notna()]
X_train = train_df[features_oddana]
y_train = train_df[target_oddana]

X_tr, X_te, y_tr, y_te = train_test_split(
    X_train, y_train, test_size=0.2, random_state=42
)
model_oddana = RandomForestRegressor(n_estimators=100, random_state=42)
model_oddana.fit(X_tr, y_tr)
y_pred_test = model_oddana.predict(X_te)

mae = mean_absolute_error(y_te, y_pred_test)
rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
r2 = r2_score(y_te, y_pred_test)
print(f"Oddana: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.2f}")

# Przewiduj brakujące wartości energii oddanej
predict_df = df[df[target_oddana].isna()]
if len(predict_df) > 0:
    X_pred = predict_df[features_oddana]
    y_pred = model_oddana.predict(X_pred)
    df.loc[df[target_oddana].isna(), target_oddana] = y_pred

# Zapisz dane z przewidywaną energią oddaną
df.to_excel("data/output/sold_predicted.xlsx", index=False)
print("Zapisano dane z przewidywaną energią oddaną do predicted_oddana.xlsx")

# Przygotuj tabelę przestawną dla energii sprzedanej
pivot_sold = df.pivot_table(
    index="hour", columns="date", values="sold_energy", aggfunc="sum"
)
pivot_sold.index = pivot_sold.index + 1  # godziny od 1 do 24
pivot_sold.index.name = "hour"

# Zapisz do pliku Excel
pivot_sold.to_excel("data/output/sold_pivot.xlsx", float_format="%.2f")
print("Dane zapisane do transformed_sold_energy.xlsx")
