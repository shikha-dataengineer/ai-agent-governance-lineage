"""
real_agent.py
--------------
A loan approval agent that runs against the REAL public dataset's actual
fields (see real_data_loader.py). Same `overreach` pattern as the
synthetic demo: when True, it also reads Gender and Property_Area --
simulating a very real and well-documented failure mode in lending
models (using demographic/location signals as proxies), which our
governance agent should catch.

All reads go through DataAccessLayer.read_field(), so the access log
is real and auditable, exactly like the synthetic demo.
"""

from dataclasses import dataclass
from data_access import DataAccessLayer


@dataclass
class Decision:
    agent_name: str
    customer_id: str
    decision: str
    reasoning_summary: str
    fields_used: dict


class RealLoanApprovalAgent:
    name = "real_loan_approval_agent"

    def __init__(self, data_layer: DataAccessLayer, overreach: bool = False):
        self.data_layer = data_layer
        self.overreach = overreach

    def evaluate(self, customer_id: str) -> Decision:
        read = lambda field: self.data_layer.read_field(self.name, customer_id, field)

        applicant_income = read("ApplicantIncome") or 0
        coapplicant_income = read("CoapplicantIncome") or 0
        loan_amount = read("LoanAmount")
        loan_term = read("Loan_Amount_Term")
        credit_history = read("Credit_History")
        education = read("Education")
        self_employed = read("Self_Employed")

        fields_used = {
            "ApplicantIncome": applicant_income,
            "CoapplicantIncome": coapplicant_income,
            "LoanAmount": loan_amount,
            "Loan_Amount_Term": loan_term,
            "Credit_History": credit_history,
            "Education": education,
            "Self_Employed": self_employed,
        }

        gender_penalty = 0
        if self.overreach:
            gender = read("Gender")
            property_area = read("Property_Area")
            fields_used["Gender"] = gender
            fields_used["Property_Area"] = property_area
            # toy (and deliberately problematic) logic: undocumented penalty
            # based on demographic/location fields that should never be used
            if gender == "Female":
                gender_penalty += 10
            if property_area == "Rural":
                gender_penalty += 10

        total_income = applicant_income + coapplicant_income

        # Handle real-world missing data (this dataset has real NaNs)
        if loan_amount is None or loan_term is None or credit_history is None:
            decision = "MANUAL_REVIEW"
            reasoning = (
                f"total_income={total_income}, but one or more required fields "
                f"(LoanAmount/Loan_Amount_Term/Credit_History) is missing in the source data "
                f"-> routed to manual review rather than an automated decision."
            )
        else:
            # simple, transparent scoring: bigger income relative to loan
            # amount is good, missed credit history is bad
            income_to_loan_ratio = total_income / max(loan_amount, 1)
            score = (
                income_to_loan_ratio * 10
                + (20 if credit_history == 1 else -30)
                + (5 if education == "Graduate" else 0)
                - gender_penalty
            )
            approved = score > 25
            decision = "APPROVED" if approved else "DENIED"
            reasoning = (
                f"total_income={total_income}, loan_amount={loan_amount}, "
                f"income_to_loan_ratio={income_to_loan_ratio:.2f}, credit_history={credit_history}, "
                f"computed_score={score:.1f} -> {decision}"
            )
            if self.overreach:
                reasoning += f" (demographic penalty applied: -{gender_penalty})"

        return Decision(
            agent_name=self.name,
            customer_id=customer_id,
            decision=decision,
            reasoning_summary=reasoning,
            fields_used=fields_used,
        )
