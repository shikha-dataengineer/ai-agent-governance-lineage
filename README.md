# AI Agent Governance & Audit-Lineage Layer

A working prototype of an agent that **watches other AI agents** — reconstructing
*why* they made each decision from real data lineage, and flagging when they
access data outside their declared scope (a "least-privilege violation").

This targets a real, current gap: as of 2026, most organizations deploying AI
agents in finance have no dedicated governance layer, and can't prove *what
data an agent actually touched* to justify a decision. The EU AI Act's
high-risk classification for autonomous financial agents requires exactly
this kind of artifact-level evidence (audit trails, not verbal assurances).

## Why this design, not just "an LLM that reviews logs"

The judgment calls here (did the agent break policy? what data caused this
decision?) are made with **deterministic, rule-based logic against a real
access log** — not an LLM guessing. That's intentional: a compliance/audit
finding needs to be reproducible and defensible in front of a regulator. An
LLM could optionally be layered on top just to phrase the final explanation
more naturally, but it should never be the thing deciding whether a violation
occurred.

## Architecture

```
customer_data.py       Synthetic applicant dataset (includes sensitive
                        fields like ssn, religion, zip_code that NO agent
                        should legitimately need — lets us test violations)

data_access.py          DataAccessLayer: the ONLY way agents may read data.
                         Every field read, by every agent, for every
                         customer, is logged. This is what makes real
                         auditing possible.

policies.py              Declares each agent's least-privilege scope: the
                         exact fields it's allowed to touch, and why.

agents.py                Two toy financial agents:
                            - LoanApprovalAgent (has an `overreach` mode
                              that simulates a real bug: reading zip_code
                              as an undocumented feature — a classic
                              redlining-adjacent violation)
                            - FraudFlaggingAgent (stays in scope)

governance_agent.py       THE CORE PRODUCT. Given a decision + the access
                          log it produced:
                            1. Reconstructs a plain-English explanation
                               grounded ONLY in fields actually read
                               (real lineage, not inference)
                            2. Checks actual field access against the
                               declared policy -> flags violations
                            3. Produces an AuditRecord per decision

report_generator.py       Turns all AuditRecords into a single Markdown
                          compliance report.

main.py                   Runs the whole pipeline end to end.
```

## How to run it

```bash
cd agent-governance-lineage
python3 main.py
```

This will:
1. Generate 25 synthetic loan applicants
2. Run both agents against them through the logged data-access layer
3. Run the governance agent to audit every decision
4. Print a summary to the console
5. Write a full Markdown audit report to `reports/audit_report.md`

### Try both scenarios

Open `main.py` and toggle:

```python
OVERREACH = True   # loan agent reads zip_code -> governance agent catches it
OVERREACH = False  # loan agent stays in scope -> clean report, zero violations
```

This is the important part to show off in a demo: the same governance agent,
with zero changes, correctly reports **0 violations** on the clean run and
**25/25 flagged** on the overreaching run — because it's checking real
logged behavior, not asserting an opinion.

## What each output actually proves

Example from the audit report when `OVERREACH = True`:

```
### loan_approval_agent -> CUST00001: DENIED
Explanation (reconstructed from actual data access, not inferred):
> The loan approval agent reached 'DENIED' for CUST00001 based on the
> following data points it actually accessed: credit_score=782,
> income=90800.47, existing_debt=45047.14, employment_years=3.1,
> requested_loan_amount=14947.86, zip_code=16328...

⚠ Governance findings:
- [HIGH] least_privilege_violation: read field 'zip_code', which is
  outside its declared scope (Assess creditworthiness for a loan
  application using financial standing only.)
```

This is genuinely useful: it's the difference between a bank *saying* "our
loan agent only uses financial data" and being able to *prove* it, decision
by decision, from an actual audit trail.

## Bonus: running this against a REAL public dataset

Everything above uses fake, made-up data. There's now a second version that
runs the exact same governance agent against a **real, public dataset of
614 actual (anonymized) loan applications** -- the well-known "Loan
Prediction" dataset used widely in ML tutorials and competitions.

New files added for this:
- `real_data_loader.py` -- loads the real CSV into the same customer format
- `real_policies.py` -- declares the real agent's allowed fields
- `real_agent.py` -- a loan agent using the REAL dataset's actual field
  names (ApplicantIncome, CoapplicantIncome, LoanAmount, Credit_History,
  Education, Self_Employed), with the same `overreach` toggle -- except
  now it reads real demographic fields (`Gender`, `Property_Area`) that
  were genuinely collected in the original dataset, not invented by us.
- `main_real_data.py` -- runs the whole pipeline against real data

### How to run it

```bash
# 1. Download the real dataset (only needs to be done once)
curl -o data/real_loan_dataset.csv https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv

# 2. Run the governance agent against it
python3 main_real_data.py
```

(No `curl` on Windows? Just paste that URL into your browser, and use
"Save As" to save it as `data/real_loan_dataset.csv`.)

### What's genuinely interesting about the real-data run

- The dataset has **real missing values** (some applicants are missing
  LoanAmount, Credit_History, etc.) -- the agent correctly routes those
  to `MANUAL_REVIEW` instead of guessing, which is realistic behavior.
- `Gender` and `Property_Area` are REAL fields that were actually
  collected about real applicants. Using them as scoring inputs is a
  well-documented, real compliance problem in lending (proxy
  discrimination / fair lending violations) -- so this isn't a
  hypothetical test case, it's the actual failure mode regulators care
  about, run against actual data.
- Same result pattern as the synthetic demo: **0 violations** when the
  agent behaves, **1,228 violations caught** (2 per applicant, across
  614 applicants) when it overreaches -- proving the governance layer's
  logic generalizes beyond the toy dataset it was originally built against.

## How to extend this (good next steps for a portfolio project)

1. **Multi-hop lineage** — currently the governance agent audits a single
   agent's decision. Extend it to trace a decision that depends on an
   *upstream* agent's output (e.g., a credit-limit agent that consumes the
   fraud agent's risk score) — this is where "blast radius" reasoning from
   real data lineage tools gets interesting.
2. **Real-time interception** — wrap `DataAccessLayer.read_field` to reject
   (not just log) out-of-policy reads live, turning this from a
   post-hoc auditor into a runtime guardrail.
3. **Add an LLM explanation layer** — swap `build_plain_english_explanation`
   in `governance_agent.py` for a call to Claude that turns the structured
   fields_used + reasoning trace into a more natural narrative, while
   keeping the violation detection itself rule-based.
4. **Map findings to actual frameworks** — extend `GovernanceFinding` to
   tag each violation with the specific regulation it maps to (e.g. "OWASP
   LLM06 Excessive Agency", "SOC2 CC6.3", "EU AI Act Art. 26") — this is
   what turns a toy audit into something a real compliance team would
   recognize.
5. **Persist the access log** — write `data_layer.access_log` to a real
   store (SQLite/Postgres) instead of an in-memory list, and build a small
   dashboard (Streamlit is a fast option) over historical audit records.

## How to talk about this in an interview / portfolio

> "Most AI-in-finance projects show an agent making decisions. I built the
> layer that's missing across the industry right now: something that
> watches AI agents and proves, from real data-access logs, whether they
> stayed within their declared scope — and reconstructs an auditable
> explanation for every decision instead of trusting the agent's own
> summary. It's a data engineering problem (lineage, structured logging,
> policy-as-code) rather than a modeling problem, which is where I wanted
> to demonstrate depth."
