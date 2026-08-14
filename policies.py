"""
policies.py
------------
Declares the LEAST-PRIVILEGE policy for each agent: the exact set of
fields it is allowed to access, and why.

In a real bank this would come from a data governance catalog (e.g.
Collibra/Alation tagging) or an IAM-style policy document. Here it's
a simple dict so the project stays runnable end-to-end, but the shape
mirrors how a real policy-as-code system would define agent scopes.
"""

AGENT_POLICIES = {
    "loan_approval_agent": {
        "allowed_fields": [
            "credit_score",
            "income",
            "existing_debt",
            "employment_years",
            "requested_loan_amount",
        ],
        "purpose": "Assess creditworthiness for a loan application using financial standing only.",
    },
    "fraud_flagging_agent": {
        "allowed_fields": [
            "recent_txn_velocity",
            "avg_txn_amount",
            "device_change_flag",
            "location_mismatch_flag",
        ],
        "purpose": "Detect anomalous transaction behavior indicating possible fraud.",
    },
}
