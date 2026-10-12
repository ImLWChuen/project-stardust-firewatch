"""Statistical regression and agreement metrics (R2, RMSE, MAE)."""
import numpy as np

def calculate_metrics(y_true, y_pred):
    """Compute regression agreement metrics (currently RMSE) between true and predicted values."""
    rmse = np.sqrt(np.mean((np.array(y_true) - np.array(y_pred)) ** 2))
    return {"rmse": float(rmse)}
