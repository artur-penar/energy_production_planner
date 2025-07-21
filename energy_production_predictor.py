from base_predictor import BasePredictor


class EnergyProductionPredictor(BasePredictor):
    def __init__(self, input_path, output_pred_path, output_pivot_path):
        super().__init__(
            input_path=input_path,
            output_pred_path=output_pred_path,
            output_pivot_path=output_pivot_path,
            features=["temp", "gti", "cloud", "hour", "month"],
            target="produced_energy",
            pivot_value="produced_energy",
        )


if __name__ == "__main__":
    predictor = EnergyProductionPredictor(
        input_path="data/input/production_to_predict.xlsx",
        output_pred_path="data/input/pv_predicted.xlsx",
        output_pivot_path="data/output/pv_pivot.xlsx",
    )
    predictor.run()
