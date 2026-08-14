"""
agents.py
----------
Two toy financial agents:

  1. LoanApprovalAgent  -- scores creditworthiness and approves/denies a loan
  2. FraudFlaggingAgent -- flags a transaction pattern as suspicious or not

Both READ ONLY through DataAccessLayer.read_field(), so every field they
touch is logged. This is what lets the governance agent later reconstruct
"why" a decision was made and check it against the declared policy.

IMPORTANT: to make this a realistic and useful demo, LoanApprovalAgent has
an `overreach` flag. When True, it simulates a real-world failure mode --
a well-intentioned engineer added zip_code as a feature to "improve model
performance" without realizing zip_code is a proxy for protected
characteristics (a classic redlining-adjacent violation). This lets us
prove the governance agent actually catches a violation, not just report
"all clear" on a toy that was designed to pass.
"""

from dataclasses import dataclass
from data_access import DataAccessLayer


@dataclass
class Decision:
    agent_name: str
    customer_id: str
    decision: str
    reasoning_summary: str
    fields_used: dict  # field_name -> value, exactly what was read


class LoanApprovalAgent:
    name = "loan_approval_agent"

    def __init__(self, data_layer: DataAccessLayer, overreach: bool = False):
        self.data_layer = data_layer
        self.overreach = overreach  # simulates a policy-violating version of the agent

    def evaluate(self, customer_id: str) -> Decision:
        read = lambda field: self.data_layer.read_field(self.name, customer_id, field)

        credit_score = read("credit_score")
        income = read("income")
        existing_debt = read("existing_debt")
        employment_years = read("employment_years")
        requested_loan_amount = read("requested_loan_amount")

        fields_used = {
            "credit_score": credit_score,
            "income": income,
            "existing_debt": existing_debt,
            "employment_years": employment_years,
            "requested_loan_amount": requested_loan_amount,
        }

        # simulate a policy violation: an "improved" version of the agent
        # also reads zip_code, treating it as a signal -- this is exactly
        # the kind of scope creep the governance agent should catch
        zip_penalty = 0
        if self.overreach:
            zip_code = read("zip_code")
            fields_used["zip_code"] = zip_code
            # toy logic: certain zip codes get an undocumented penalty
            zip_penalty = 15 if zip_code.startswith(("1", "2")) else 0

        debt_to_income = existing_debt / income if income > 0 else 1.0
        score = (
            (credit_score - 500) * 0.3
            + (employment_years * 5)
            - (debt_to_income * 100)
            - (requested_loan_amount / income * 50 if income > 0 else 50)
            - zip_penalty
        )

        approved = score > 40
        decision = "APPROVED" if approved else "DENIED"

        reasoning = (
            f"credit_score={credit_score}, debt_to_income={debt_to_income:.2f}, "
            f"employment_years={employment_years}, computed_score={score:.1f} -> {decision}"
        )
        if self.overreach:
            reasoning += f" (zip_code penalty applied: -{zip_penalty})"

        return Decision(
            agent_name=self.name,
            customer_id=customer_id,
            decision=decision,
            reasoning_summary=reasoning,
            fields_used=fields_used,
        )


class FraudFlaggingAgent:
    name = "fraud_flagging_agent"

    def __init__(self, data_layer: DataAccessLayer):
        self.data_layer = data_layer

    def evaluate(self, customer_id: str) -> Decision:
        read = lambda field: self.data_layer.read_field(self.name, customer_id, field)

        velocity = read("recent_txn_velocity")
        avg_amount = read("avg_txn_amount")
        device_change = read("device_change_flag")
        location_mismatch = read("location_mismatch_flag")

        fields_used = {
            "recent_txn_velocity": velocity,
            "avg_txn_amount": avg_amount,
            "device_change_flag": device_change,
            "location_mismatch_flag": location_mismatch,
        }

        risk_score = 0
        if velocity > 40:
            risk_score += 30
        if avg_amount > 2000:
            risk_score += 20
        if device_change:
            risk_score += 25
        if location_mismatch:
            risk_score += 30

        flagged = risk_score >= 50
        decision = "FLAGGED" if flagged else "CLEAR"

        reasoning = (
            f"velocity={velocity}, avg_amount={avg_amount}, device_change={device_change}, "
            f"location_mismatch={location_mismatch}, risk_score={risk_score} -> {decision}"
        )

        return Decision(
            agent_name=self.name,
            customer_id=customer_id,
            decision=decision,
            reasoning_summary=reasoning,
            fields_used=fields_used,
        )
