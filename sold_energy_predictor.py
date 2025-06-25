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
        self.features = ["produced_energy", "hour", "is_holiday", "day_of_week", "month"]
        self.target = "sold_energy"
        self.df = None
        self.model = None
        self.mae = None
        self.rmse = None
        self.r2 = None

    def load_data(self, df):
        self.df = df.copy()

    def load_data_from_excel(self):
        self.df = pd.read_excel(self.input_path)
        self.df.columns = self.df.columns.str.strip()
        print(self.df.columns.tolist())
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        if self.df["date"].dtype != "O":
            self.df["date"] = self.df["date"].dt.date


    def train_model(self):
        train_df = self.df[self.df[self.target].notna()]
        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_tr, X_te, y_tr, y_te = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42
        )
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_tr, y_tr)
        y_pred_test = self.model.predict(X_te)
        self.mae = mean_absolute_error(y_te, y_pred_test)
        self.rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
        self.r2 = r2_score(y_te, y_pred_test)
        print(f"Oddana: MAE={self.mae:.2f}, RMSE={self.rmse:.2f}, R2={self.r2:.2f}")

    def predict_missing(self):
        predict_df = self.df[self.df[self.target].isna()]
        if len(predict_df) > 0:
            X_pred = predict_df[self.features]
            y_pred = self.model.predict(X_pred)
            self.df.loc[self.df[self.target].isna(), self.target] = y_pred

    def save_predictions(self):
        self.df.to_excel(self.output_pred_path, index=False)
        print(f"Zapisano dane z przewidywaną energią oddaną do {self.output_pred_path}")

    def save_pivot(self):
        pivot_sold = self.df.pivot_table(
            index="hour", columns="date", values="sold_energy", aggfunc="sum"
        )
        pivot_sold.index = pivot_sold.index + 1  # godziny od 1 do 24
        pivot_sold.index.name = "hour"
        # Uzupełnij NaN na 0, wymuś typ float dla sumy
        pivot_sold = pivot_sold.astype(float).fillna(0)
        pivot_sold = pivot_sold / 1000  # Przekształć na MWh
        # Dodaj wiersz z sumą na końcu
        pivot_sold.loc['SUMA'] = pivot_sold.sum(numeric_only=True)
        pivot_sold.to_excel(self.output_pivot_path, float_format="%.3f")
        print(f"Dane zapisane do {self.output_pivot_path}")

    def test_features_combinations(self):
        feature_sets = [
            (["produced_energy", "hour", "is_holiday"], "is_holiday"),
            (["produced_energy", "hour", "day_of_week"], "day_of_week"),
            (["produced_energy", "hour", "is_holiday", "day_of_week"], "is_holiday + day_of_week"),
            (["produced_energy", "hour", "is_holiday", "day_of_week", "month"], "is_holiday + day_of_week + month"),
        ]
        results = []
        for features, label in feature_sets:
            train_df = self.df[self.df[self.target].notna()]
            X_train = train_df[features]
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
            results.append((label, mae, rmse, r2))
        print("\nPorównanie skuteczności modeli:")
        print(f"{'Cechy':<35} {'MAE':<10} {'RMSE':<10} {'R2':<10}")
        for label, mae, rmse, r2 in results:
            print(f"{label:<35} {mae:<10.2f} {rmse:<10.2f} {r2:<10.2f}")

    def run(self):
        self.load_data_from_excel()
        self.train_model()
        self.predict_missing()
        self.save_pivot()

if __name__ == "__main__":
    predictor = SoldEnergyPredictor(
        input_path="data/input/pv_predicted.xlsx",
        output_pred_path="data/output/sold_predicted.xlsx",
        output_pivot_path="data/output/sold_pivot.xlsx"
    )
    predictor.load_data_from_excel()
    predictor.test_features_combinations()
    predictor.run()
