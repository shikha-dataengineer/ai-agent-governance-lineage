"""
report_generator.py
--------------------
Turns the list of AuditRecords into a single Markdown audit report --
the kind of artifact-level evidence document a compliance reviewer or
auditor would actually want to see (this maps to what regulators now
call "artifact-level evidence": model cards, data lineage, audit trails).
"""

from datetime import datetime, timezone
from governance_agent import summarize_violations


def generate_markdown_report(audit_records: list, policies: dict) -> str:
    summary = summarize_violations(audit_records)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# AI Agent Governance & Audit Report",
        f"_Generated: {timestamp}_",
        "",
        "## 1. Scope",
        f"This report covers {len(audit_records)} agent decisions across "
        f"{len(set(r.agent_name for r in audit_records))} agents and "
        f"{len(set(r.customer_id for r in audit_records))} customer records.",
        "",
        "## 2. Declared Agent Policies (Least Privilege)",
    ]

    for agent_name, policy in policies.items():
        lines.append(f"- **{agent_name}**: {policy['purpose']}")
        lines.append(f"  - Allowed fields: {', '.join(policy['allowed_fields'])}")

    lines += [
        "",
        "## 3. Violation Summary",
        f"- **Total violations found:** {summary['total_violations']}",
    ]
    if summary["by_agent"]:
        for agent, count in summary["by_agent"].items():
            lines.append(f"  - {agent}: {count} violation(s)")
    else:
        lines.append("  - No violations found. All agents stayed within declared scope.")

    lines += ["", "## 4. Per-Decision Audit Trail", ""]

    # Flag violating records first so reviewers see the important ones immediately
    sorted_records = sorted(audit_records, key=lambda r: len(r.violations), reverse=True)
    for record in sorted_records:
        lines.append(record.to_report_block())
        lines.append("")

    return "\n".join(lines)


def save_report(content: str, path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
