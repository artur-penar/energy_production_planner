import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Wczytaj dane z pliku Excel
df = pd.read_excel("data/data_to_predict.xlsx")
df.columns = df.columns.str.strip()

print(df.columns.tolist())
df["date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
df["date"] = df["date"].dt.date

# Wybierz cechy pogodowe i czasowe
features_pv = ["temp", "gti", "cloud", "hour", "is_holiday"]
target_pv = "produced_energy"

train_df = df[df[target_pv].notna()]
X_train = train_df[features_pv]
y_train = train_df[target_pv]

X_tr, X_te, y_tr, y_te = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
model_pv = RandomForestRegressor(n_estimators=100, random_state=42)
model_pv.fit(X_tr, y_tr)
y_pred_test = model_pv.predict(X_te)

mae = mean_absolute_error(y_te, y_pred_test)
rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
r2 = r2_score(y_te, y_pred_test)
print(f"PV: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.2f}")

# Przewiduj brakujące wartości PV
predict_df = df[df[target_pv].isna()]
if len(predict_df) > 0:
    X_pred = predict_df[features_pv]
    y_pred = model_pv.predict(X_pred)
    df.loc[df[target_pv].isna(), target_pv] = y_pred

# Zapisz dane z przewidywaną produkcją PV
df.to_excel("data/predicted_pv.xlsx", index=False)
print("Zapisano dane z przewidywaną produkcją PV do predicted_pv.xlsx")

# Przygotuj tabelę przestawną dla rco 243 kW
produced_pivot = df.pivot_table(
    index="hour", columns="date", values="produced_energy", aggfunc="sum"
)
produced_pivot.index = produced_pivot.index + 1  # godziny od 1 do 24
produced_pivot.index.name = "hour"

# Zapisz do pliku Excel
produced_pivot.to_excel("predicted_energy_production_transformed.xlsx", float_format="%.2f")
print("Dane zapisane do predicted_energy_production.xlsx")