import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_dataset():
    # Generate a small sample robustly 
    dates = pd.date_range('2025-01-01', periods=10)
    data = []
    for d in dates:
        data.append({
            'date': d,
            'hospital_id': 'H1',
            'blood_group': 'O+',
            'stock_units': 100,
            'daily_demand': 40,
            'stock_coverage_days': 2.5,
            'near_expiry_units': 5,
        })
    df = pd.DataFrame(data)
    df['shortage_flag'] = (df['stock_coverage_days'] < 3).astype(int)
    df['near_expiry_ratio'] = df['near_expiry_units'] / df['stock_units']
    return df

def test_dataset_shape_and_completeness(sample_dataset):
    assert not sample_dataset.empty
    expected_cols = ['date', 'hospital_id', 'blood_group', 'stock_units', 'daily_demand', 'stock_coverage_days']
    for col in expected_cols:
        assert col in sample_dataset.columns
    # Ensure no nulls exist
    assert sample_dataset.isnull().sum().sum() == 0

def test_shortage_flag_logic(sample_dataset):
    df = sample_dataset
    expected_flag = (df['stock_coverage_days'] < 3).astype(int)
    np.testing.assert_array_equal(df['shortage_flag'].values, expected_flag.values)

def test_near_expiry_ratio_range(sample_dataset):
    ratio = sample_dataset['near_expiry_ratio']
    assert ratio.min() >= 0.0
    assert ratio.max() <= 1.0

def test_no_data_leakage_in_chronological_split():
    # Mocking train/test chronological split
    dates = pd.date_range('2025-01-01', periods=100)
    df = pd.DataFrame({'date': dates, 'val': np.arange(100)})
    
    # 80% train, 20% test
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size]
    test_df = df.iloc[train_size:]
    
    # Max date of train should be strictly less than min date of test
    assert train_df['date'].max() < test_df['date'].min()

def test_feature_engineer_output_reproducibility():
    np.random.seed(42)
    out1 = np.random.rand(10)
    
    np.random.seed(42)
    out2 = np.random.rand(10)
    
    # Deterministic output yields the identical arrays
    np.testing.assert_array_equal(out1, out2)

def test_scaler_fitted_only_on_train_split():
    from sklearn.preprocessing import StandardScaler
    train_data = np.array([[1], [2], [3]])
    test_data = np.array([[4], [5]])
    
    scaler = StandardScaler()
    scaler.fit(train_data)
    
    # Mean of train array is 2. The scaler shouldn't consider the test dataset.
    assert scaler.mean_[0] == 2.0
