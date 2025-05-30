import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Dane: Prognoza i Realnie
wyprodukowana_prognoza = np.array([2.0119, 3.5057, 4.5099, 1.5329, 3.6213, 0.310])
wyprodukowana_realnie = np.array([1.8911, 2.6479, 4.8616, 1.4235, 3.9806, 0.9077])

oddana_prognoza = np.array([0.3629, 1.1787, 1.5689, 0.1625, 1.5759, 0.000])
oddana_realnie = np.array([1.1875, 2.3673, 1.9218, 0.0035, 0.9050, 0.0003])

# Funkcja do obliczania metryk
def calculate_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    return mae, mse, rmse, r2

# Obliczenia dla "Wyprodukowana"
wyprodukowana_metrics = calculate_metrics(wyprodukowana_realnie, wyprodukowana_prognoza)
print("Wyprodukowana:")
print(f"MAE: {wyprodukowana_metrics[0]:.4f}")
print(f"MSE: {wyprodukowana_metrics[1]:.4f}")
print(f"RMSE: {wyprodukowana_metrics[2]:.4f}")
print(f"R²: {wyprodukowana_metrics[3]:.4f}")

# Obliczenia dla "Oddana"
oddana_metrics = calculate_metrics(oddana_realnie, oddana_prognoza)
print("\nOddana:")
print(f"MAE: {oddana_metrics[0]:.4f}")
print(f"MSE: {oddana_metrics[1]:.4f}")
print(f"RMSE: {oddana_metrics[2]:.4f}")
print(f"R²: {oddana_metrics[3]:.4f}")
