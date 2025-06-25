import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class EnergyProductionPredictor:
    def __init__(self, input_path, output_pred_path, output_pivot_path):
        self.input_path = input_path
        self.output_pred_path = output_pred_path
        self.output_pivot_path = output_pivot_path
        self.features = ["temp", "gti", "cloud", "hour", "month"]
        self.target = "produced_energy"
        self.df = None
        self.model = None
        self.mae = None
        self.rmse = None
        self.r2 = None

    def load_data_from_excel(self):
        self.df = pd.read_excel(self.input_path)
        self.df.columns = self.df.columns.str.strip()
        print(self.df.columns.tolist())
        self.df["date"] = pd.to_datetime(self.df["date"], format="%d.%m.%Y")
        self.df["date"] = self.df["date"].dt.date

    def load_data(self, df):
        self.df = df.copy()
    

    def train_model(self):
        train_df = self.df[self.df[self.target].notna()]
        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_tr, X_te, y_tr, y_te = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_tr, y_tr)
        y_pred_test = self.model.predict(X_te)
        self.mae = mean_absolute_error(y_te, y_pred_test)
        self.rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
        self.r2 = r2_score(y_te, y_pred_test)
        print(f"PV: MAE={self.mae:.2f}, RMSE={self.rmse:.2f}, R2={self.r2:.2f}")

    def predict_missing(self):
        predict_df = self.df[self.df[self.target].isna()]
        if len(predict_df) > 0:
            X_pred = predict_df[self.features]
            y_pred = self.model.predict(X_pred)
            self.df.loc[self.df[self.target].isna(), self.target] = y_pred

    def save_predictions(self):
        self.df.to_excel(self.output_pred_path, index=False)
        print(f"Zapisano dane z przewidywaną produkcją PV do {self.output_pred_path}")

    def save_pivot(self):
        produced_pivot = self.df.pivot_table(
            index="hour", columns="date", values="produced_energy", aggfunc="sum"
        )
        if produced_pivot.empty or produced_pivot.shape[1] == 0:
            print("Brak danych do zapisania pivotu - nie utworzono pliku.")
            return
        produced_pivot.index = produced_pivot.index + 1  # godziny od 1 do 24
        produced_pivot.index.name = "hour"
        produced_pivot = produced_pivot.astype(float).fillna(0)
        produced_pivot = produced_pivot / 1000 # przeliczenie na MWh
        produced_pivot.loc['SUMA'] = produced_pivot.sum(numeric_only=True)
        produced_pivot.to_excel(self.output_pivot_path, float_format="%.3f")
        print(f"Dane zapisane do {self.output_pivot_path}")

    def test_features_combinations(self):
        feature_sets = [
            (["temp", "gti", "cloud", "hour"], "bez 'month'"),
            (["temp", "gti", "cloud", "hour", "month"], "z 'month'")
        ]
        results = []
        train_df = self.df[self.df[self.target].notna()]
        for features, label in feature_sets:
            X_train = train_df[features]
            y_train = train_df[self.target]
            X_tr, X_te, y_tr, y_te = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_tr, y_tr)
            y_pred_test = model.predict(X_te)
            mae = mean_absolute_error(y_te, y_pred_test)
            rmse = np.sqrt(mean_squared_error(y_te, y_pred_test))
            r2 = r2_score(y_te, y_pred_test)
            results.append((label, mae, rmse, r2))
        print("\nPorównanie skuteczności modeli:")
        print(f"{'Cechy':<15} {'MAE':<10} {'RMSE':<10} {'R2':<10}")
        for label, mae, rmse, r2 in results:
            print(f"{label:<15} {mae:<10.2f} {rmse:<10.2f} {r2:<10.2f}")

    def test(self):
        """Porównuje skuteczność modelu bez oraz z cechą 'month'."""
        self.load_data_from_excel()
        self.test_features_combinations()

    def run(self):
        self.load_data_from_excel()
        self.train_model()
        self.predict_missing()
        self.save_predictions()
        self.save_pivot()

if __name__ == "__main__":
    predictor = EnergyProductionPredictor(
        input_path="data/input/production_to_predict.xlsx",
        output_pred_path="data/input/pv_predicted.xlsx",
        output_pivot_path="data/output/pv_pivot.xlsx"
    )
    predictor.run()