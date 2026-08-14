"""
real_data_loader.py
--------------------
Loads a REAL, public loan-applicant dataset (the well-known "Loan
Prediction" dataset, widely used in ML tutorials/competitions) and
converts it into the same customer-record format the rest of this
project already uses.

Source: https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv
614 real (anonymized) loan applications with columns:
    Loan_ID, Gender, Married, Dependents, Education, Self_Employed,
    ApplicantIncome, CoapplicantIncome, LoanAmount, Loan_Amount_Term,
    Credit_History, Property_Area, Loan_Status

This is a REAL dataset with real messiness (missing values in several
columns), which is exactly the kind of data our governance agent should
be robust to.

Note: Gender, Married, Dependents, and Property_Area are included in the
raw data (they were originally collected as demographic context) but are
NOT part of any agent's declared policy scope below -- a real loan agent
should not condition decisions on protected characteristics or location
proxies. That makes this dataset a genuinely good test: if an agent
"accidentally" reads Gender or Property_Area, that's a real, well-known
compliance red flag (proxy discrimination / fair lending violation),
not one we invented for the demo.
"""

import math
import pandas as pd

DATASET_URL = "https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv"
LOCAL_PATH = "data/real_loan_dataset.csv"


def _clean_value(v):
    """Convert pandas NaN to Python None so downstream code doesn't choke on NaN comparisons."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def load_real_customers(path: str = LOCAL_PATH) -> list:
    """
    Loads the CSV (must already be downloaded to `path`) and returns a
    list of dicts, one per applicant, using the ORIGINAL column names
    from the dataset (so it's obviously real, not remapped to look like
    our synthetic schema).
    """
    df = pd.read_csv(path)
    customers = []
    for _, row in df.iterrows():
        record = {col: _clean_value(row[col]) for col in df.columns}
        record["customer_id"] = record.pop("Loan_ID")  # keep a consistent key name for DataAccessLayer
        customers.append(record)
    return customers
