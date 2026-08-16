# AI Agent Governance & Audit-Lineage Layer

Banks are starting to use AI agents to approve loans, flag fraud, that kind of thing. But most of them can't actually prove *what data* those agents used to make a decision they just trust the agent. That's a real problem, especially when an agent might be quietly using something like zip code that it has no business looking at.

This project is my attempt at building the missing piece: a second agent that watches the first one, logs everything it reads, and checks it against a rulebook of what it's actually allowed to touch.

## What it actually does

- Every time an agent reads a piece of data, it gets logged (who read what, for which customer).
- A separate governance agent compares that log against a declared policy e.g. the loan agent is only allowed to look at income, credit score, and debt.
- If the agent reads something outside that policy, it gets flagged, with a plain-English explanation of what happened and why it matters.
- Everything's written out to a Markdown audit report at the end.

I tested this two ways:
1. On made-up data first, to make sure the logic worked.
2. On a real public dataset of 614 loan applications, to make sure it held up on messy real data.

Same result both times: when I made the agent behave, it correctly found zero violations. When I made it read fields it shouldn't (gender, property area), it caught every single one - 1,228 violations across 614 applicants.

## Why rule-based, not an LLM

I kept the actual violation-detection logic rule-based on purpose. For something that's essentially a compliance check, you want the same input to always give the same output an LLM guessing at is this a violation isn't something you would want to hand a regulator. An LLM could be layered on top later just to make the explanations read more naturally, but it shouldn't be the thing deciding what counts as a violation.

## Project structure

```
customer_data.py       fake customer data (includes fields no agent should need, on purpose)
data_access.py         the only way agents can read data — logs every read
policies.py             declares what each agent is allowed to access
agents.py                the two toy agents (loan approval, fraud flagging)
governance_agent.py       the auditor — checks logs against policy, explains decisions
report_generator.py       writes everything into a Markdown report
main.py                   run this to try it on fake data

real_data_loader.py    same idea, but for real data
real_agent.py
real_policies.py
main_real_data.py         run this to try it on the real 614-applicant dataset
```

## Running it

```bash
python3 main.py
```

Runs on fake data, writes a report to `reports/audit_report.md`.

Try flipping this in `main.py` to see both outcomes:

```python
OVERREACH = True   # agent reads a field it shouldn't -> gets caught
OVERREACH = False  # agent behaves -> clean report
```

For the real dataset:

```bash
curl -o data/real_loan_dataset.csv https://raw.githubusercontent.com/shrikant-temburwar/Loan-Prediction-Dataset/master/train.csv
python3 main_real_data.py
```

## Example from the report

```
### loan_approval_agent -> CUST00001: DENIED
Explanation (reconstructed from actual data access, not inferred):
> The loan approval agent reached 'DENIED' for CUST00001 based on the
> following data it actually accessed: credit_score=782, income=90800.47,
> existing_debt=45047.14, employment_years=3.1, requested_loan_amount=14947.86,
> zip_code=16328...

Governance findings:
- [HIGH] least_privilege_violation: read field 'zip_code', which is outside
  its declared scope.
```

## What I would add next, if I kept going

- Tracing violations across multiple agents, not just one at a time
- Blocking bad reads in real time instead of just logging them after the fact
- Mapping violations to actual regulations (EU AI Act, SOC2, etc.)
- Saving results to a real database instead of just a text report

## Stack

Python 3, pandas. No API keys or paid services needed to run it.

