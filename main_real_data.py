"""
main_real_data.py
-------------------
Runs the SAME governance agent from main.py, but against a REAL public
loan dataset (614 real, anonymized applicants) instead of synthetic data.

Run with:
    python3 main_real_data.py

Prerequisite: data/real_loan_dataset.csv must exist. If you don't have
it yet, download it with:

    curl -o data/real_loan_dataset.csv \\
      https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv

(On Windows without curl, just open that URL in your browser and
"Save As" data/real_loan_dataset.csv)
"""

import os
from data_access import DataAccessLayer
from real_data_loader import load_real_customers, LOCAL_PATH
from real_agent import RealLoanApprovalAgent
from real_policies import REAL_AGENT_POLICIES
from governance_agent import audit_all, summarize_violations
from report_generator import generate_markdown_report, save_report

OVERREACH = True  # toggle to see clean vs. violating runs, same as main.py
REPORT_PATH = "reports/real_data_audit_report.md"


def main():
    if not os.path.exists(LOCAL_PATH):
        print(f"ERROR: {LOCAL_PATH} not found.")
        print("Download it first with:")
        print(f"  curl -o {LOCAL_PATH} https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv")
        return

    print("Loading real public loan dataset...")
    customers = load_real_customers()
    print(f"Loaded {len(customers)} real applicant records.")

    data_layer = DataAccessLayer(customers)
    agent = RealLoanApprovalAgent(data_layer, overreach=OVERREACH)

    print("Running loan approval agent against real data...")
    decisions = [agent.evaluate(c["customer_id"]) for c in customers]

    decision_counts = {}
    for d in decisions:
        decision_counts[d.decision] = decision_counts.get(d.decision, 0) + 1
    print(f"Decisions: {decision_counts}")
    print(f"Logged {len(data_layer.access_log)} field-level data accesses.")

    print("Running governance agent to audit decisions against real data...")
    audit_records = audit_all(decisions, data_layer, policies=REAL_AGENT_POLICIES)
    summary = summarize_violations(audit_records)

    print()
    print("=" * 60)
    print(f"GOVERNANCE SUMMARY (real data): {summary['total_violations']} violation(s) found")
    for agent_name, count in summary["by_agent"].items():
        print(f"  - {agent_name}: {count} violation(s)")
    print("=" * 60)
    print()

    report = generate_markdown_report(audit_records, REAL_AGENT_POLICIES)
    save_report(report, REPORT_PATH)
    print(f"Full audit report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
