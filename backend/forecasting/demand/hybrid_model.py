"""
Machine Learning Pipeline: Hybrid GRU + LightGBM Demand Forecaster
Responsible for handling temporal sequences (GRU) and non-linear categorical 
features (LightGBM) to forecast blood demand using MIMIC-IV data.
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import logging

logger = logging.getLogger(__name__)

class BloodDemandGRU(nn.Module):
    """
    State-of-the-art Gated Recurrent Unit for capturing temporal dependencies
    in blood demand spikes (e.g., trauma seasonality).
    """
    def __init__(self, input_dim, hidden_dim=64, num_layers=2):
        super(BloodDemandGRU, self).__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        out = self.fc(out[:, -1, :]) # Take the last time step
        return out


class HybridDemandForecaster:
    """
    The Digital Twin Predictive Layer.
    Combines GRU (for sequence data) and LightGBM (for static/categorical data).
    """
    def __init__(self):
        self.gru_model = BloodDemandGRU(input_dim=10) # Example input dim
        self.lgb_model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.gru_model.to(self.device)

    def train_gru(self, X_seq, y_target, epochs=20):
        """Train the GRU on temporal sequences."""
        logger.info("Training GRU model on sequence data...")
        optimizer = torch.optim.Adam(self.gru_model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        dataset = TensorDataset(torch.FloatTensor(X_seq), torch.FloatTensor(y_target))
        loader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        self.gru_model.train()
        for epoch in range(epochs):
            for batch_X, batch_y in loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                predictions = self.gru_model(batch_X).squeeze()
                loss = criterion(predictions, batch_y)
                loss.backward()
                optimizer.step()
        logger.info("GRU training complete.")

    def train_lightgbm(self, X_static, y_target):
        """Train LightGBM on static/categorical features (e.g., day of week, weather)."""
        logger.info("Training LightGBM model on static features...")
        self.lgb_model.fit(X_static, y_target)
        logger.info("LightGBM training complete.")

    def predict(self, X_seq, X_static, gru_weight=0.6):
        """
        Ensemble prediction.
        Based on 2025/2026 literature, weighting the deep learning model 
        slightly higher for emergency response usually yields best results.
        """
        self.gru_model.eval()
        with torch.no_grad():
            gru_preds = self.gru_model(torch.FloatTensor(X_seq).to(self.device)).cpu().numpy().flatten()
            
        lgb_preds = self.lgb_model.predict(X_static)
        
        # The Prescriptive Output
        hybrid_preds = (gru_weight * gru_preds) + ((1 - gru_weight) * lgb_preds)
        return hybrid_preds

if __name__ == "__main__":
    # Base structure ready for the ML Lead
    print("Hybrid GRU-LightGBM architecture base ready.")
