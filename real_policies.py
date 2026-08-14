"""
real_policies.py
------------------
Declared least-privilege policy for the agent running against the REAL
public loan dataset (see real_data_loader.py). Field names match the
dataset's original columns exactly.
"""

REAL_AGENT_POLICIES = {
    "real_loan_approval_agent": {
        "allowed_fields": [
            "ApplicantIncome",
            "CoapplicantIncome",
            "LoanAmount",
            "Loan_Amount_Term",
            "Credit_History",
            "Education",
            "Self_Employed",
        ],
        "purpose": (
            "Assess loan eligibility using financial standing and credit history only -- "
            "explicitly excludes demographic/protected fields like Gender, Married, "
            "Dependents, and Property_Area to avoid proxy discrimination / fair lending violations."
        ),
    }
}
