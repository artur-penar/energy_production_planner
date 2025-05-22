import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class SoldEnergyPredictor:
    def __init__(self, input_path, output_pred_path, output_pivot_path):
        self.input_path = input_path
        self.output_pred_path = output_pred_path
        self.output_pivot_path = output_pivot_path
        self.features = ["produced_energy", "hour", "is_holiday"]
        self.target = "sold_energy"

    def run(self):
        df = pd.read_excel(self.input_path)
        df.columns = df.columns.str.strip()
        print(df.columns.tolist())
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if df["date"].dtype != "O":
            df["date"] = df["date"].dt.date

        train_df = df[df[self.target].notna()]
        X_train = train_df[self.features]
        y_train = train_df[self.target]

        X_tr, X_te, y_tr, y_te = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42
        )
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_tr, y_tr)
        y_pred_test = model.predict(X_te)

        mae = mean_absolute_error(y_te, y_pred_test)
        rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
        r2 = r2_score(y_te, y_pred_test)
        print(f"Oddana: MAE={mae:.2f}, RMSE={rmse:.2f}, R2={r2:.2f}")

        # Przewiduj brakujące wartości energii oddanej
        predict_df = df[df[self.target].isna()]
        if len(predict_df) > 0:
            X_pred = predict_df[self.features]
            y_pred = model.predict(X_pred)
            df.loc[df[self.target].isna(), self.target] = y_pred

        # Zapisz dane z przewidywaną energią oddaną
        df.to_excel(self.output_pred_path, index=False)
        print(f"Zapisano dane z przewidywaną energią oddaną do {self.output_pred_path}")

        # Przygotuj tabelę przestawną dla energii sprzedanej
        pivot_sold = df.pivot_table(
            index="hour", columns="date", values="sold_energy", aggfunc="sum"
        )
        pivot_sold.index = pivot_sold.index + 1  # godziny od 1 do 24
        pivot_sold.index.name = "hour"
        pivot_sold.to_excel(self.output_pivot_path, float_format="%.2f")
        print(f"Dane zapisane do {self.output_pivot_path}")

if __name__ == "__main__":
    predictor = SoldEnergyPredictor(
        input_path="data/input/pv_predicted.xlsx",
        output_pred_path="data/output/sold_predicted.xlsx",
        output_pivot_path="data/output/sold_pivot.xlsx"
    )
    predictor.run()
