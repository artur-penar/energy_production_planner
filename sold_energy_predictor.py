from base_predictor import BasePredictor

class SoldEnergyPredictor(BasePredictor):
    def __init__(self, input_path, output_pred_path, output_pivot_path):
        super().__init__(
            input_path=input_path,
            output_pred_path=output_pred_path,
            output_pivot_path=output_pivot_path,
            features=["produced_energy", "hour", "is_holiday", "day_of_week", "month"],  # zmień jeśli inne cechy
            target="sold_energy",
            pivot_value="sold_energy"
        )

if __name__ == "__main__":
    predictor = SoldEnergyPredictor(
        input_path="data/input/pv_predicted.xlsx",
        output_pred_path="data/output/sold_predicted.xlsx",
        output_pivot_path="data/output/sold_pivot.xlsx",
    )
    predictor.load_data_from_excel()
    predictor.run()
