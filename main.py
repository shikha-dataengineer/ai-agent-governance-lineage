"""
main.py
--------
Runs the full end-to-end demo:

  1. Generate synthetic customer/applicant data
  2. Run two toy financial agents (loan approval + fraud flagging) through
     the mediated DataAccessLayer, so every field read is logged
  3. Run the governance agent to audit those decisions:
       - reconstruct plain-English explanations grounded in real data lineage
       - check every decision against declared least-privilege policy
  4. Generate a Markdown audit report

Run with:
    python3 main.py

Try it both ways to see the detector actually work:
    OVERREACH = True   -> loan agent reads zip_code (a policy violation) -> report flags it
    OVERREACH = False  -> loan agent stays in scope -> report shows a clean pass
"""

from customer_data import generate_customers
from data_access import DataAccessLayer
from agents import LoanApprovalAgent, FraudFlaggingAgent
from governance_agent import audit_all, summarize_violations
from report_generator import generate_markdown_report, save_report
from policies import AGENT_POLICIES

# Toggle this to see the governance agent catch (or not catch) the violation
OVERREACH = True

N_CUSTOMERS = 25
REPORT_PATH = "reports/audit_report.md"


def main():
    print(f"Generating {N_CUSTOMERS} synthetic customer records...")
    customers = generate_customers(n=N_CUSTOMERS)

    data_layer = DataAccessLayer(customers)
    loan_agent = LoanApprovalAgent(data_layer, overreach=OVERREACH)
    fraud_agent = FraudFlaggingAgent(data_layer)

    print("Running loan approval and fraud flagging agents...")
    decisions = []
    for customer in customers:
        decisions.append(loan_agent.evaluate(customer["customer_id"]))
        decisions.append(fraud_agent.evaluate(customer["customer_id"]))

    print(f"Agents made {len(decisions)} decisions, generating {len(data_layer.access_log)} logged data accesses.")

    print("Running governance agent to audit decisions...")
    audit_records = audit_all(decisions, data_layer)
    summary = summarize_violations(audit_records)

    print()
    print("=" * 60)
    print(f"GOVERNANCE SUMMARY: {summary['total_violations']} violation(s) found")
    for agent, count in summary["by_agent"].items():
        print(f"  - {agent}: {count} violation(s)")
    print("=" * 60)
    print()

    report = generate_markdown_report(audit_records, AGENT_POLICIES)
    save_report(report, REPORT_PATH)
    print(f"Full audit report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
