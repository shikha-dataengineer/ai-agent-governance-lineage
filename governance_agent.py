"""
governance_agent.py
--------------------
This is the actual product: an agent that watches OTHER agents (via the
access log produced by DataAccessLayer) and:

  1. Flags least-privilege violations -- did the agent read any field
     outside its declared policy scope? (OWASP LLM06 "Excessive Agency",
     SOC2 CC6, EU AI Act Article 26 human-oversight/traceability angle)

  2. Reconstructs a plain-English "why" explanation for each decision,
     grounded ONLY in the fields that were actually read (real lineage,
     not a guess) -- this is the artifact-level evidence regulators are
     now asking for instead of verbal assurances.

  3. Produces an audit record per decision that could be handed to a
     compliance reviewer.

Detection here is deliberately rule-based (log diffing against a policy
dict), not an LLM call -- the compliance judgment must be deterministic
and reproducible. An LLM is only used, optionally, to phrase the final
explanation more naturally (see llm_explainer.py).
"""

from dataclasses import dataclass, field
from policies import AGENT_POLICIES


@dataclass
class GovernanceFinding:
    agent_name: str
    customer_id: str
    violation_type: str          # "least_privilege_violation" or None-equivalent when clean
    severity: str                 # "high", "medium", "low", "none"
    detail: str


@dataclass
class AuditRecord:
    agent_name: str
    customer_id: str
    decision: str
    plain_english_explanation: str
    fields_used: dict
    violations: list  # list[GovernanceFinding]

    def to_report_block(self) -> str:
        lines = [
            f"### {self.agent_name} -> {self.customer_id}: {self.decision}",
            f"**Explanation (reconstructed from actual data access, not inferred):**",
            f"> {self.plain_english_explanation}",
            f"**Fields this agent actually read:** {', '.join(self.fields_used.keys())}",
        ]
        if self.violations:
            lines.append("**⚠ Governance findings:**")
            for v in self.violations:
                lines.append(f"- [{v.severity.upper()}] {v.violation_type}: {v.detail}")
        else:
            lines.append("**Governance findings:** none -- agent stayed within declared policy scope.")
        return "\n".join(lines)


def check_least_privilege(agent_name: str, fields_accessed: set, policies: dict = None) -> list:
    """Compare what an agent actually read against its declared policy scope."""
    if policies is None:
        policies = AGENT_POLICIES
    policy = policies.get(agent_name)
    findings = []
    if policy is None:
        findings.append(GovernanceFinding(
            agent_name=agent_name,
            customer_id="*",
            violation_type="no_policy_defined",
            severity="high",
            detail=f"agent '{agent_name}' has no declared policy -- cannot verify least privilege at all.",
        ))
        return findings

    allowed = set(policy["allowed_fields"])
    unauthorized = fields_accessed - allowed
    for field_name in unauthorized:
        findings.append(GovernanceFinding(
            agent_name=agent_name,
            customer_id="*",  # filled in per-decision by caller
            violation_type="least_privilege_violation",
            severity="high",
            detail=(
                f"read field '{field_name}', which is outside its declared scope "
                f"({policy['purpose']}). Allowed fields: {sorted(allowed)}."
            ),
        ))
    return findings


def build_plain_english_explanation(decision, agent_name: str) -> str:
    """
    Turn the raw fields_used + reasoning into a compliance-readable
    explanation, grounded strictly in what was actually read (real
    lineage), not a post-hoc guess.
    """
    field_summary = "; ".join(f"{k}={v}" for k, v in decision.fields_used.items())
    return (
        f"The {agent_name.replace('_', ' ')} reached '{decision.decision}' for {decision.customer_id} "
        f"based on the following data points it actually accessed: {field_summary}. "
        f"Internal reasoning trace: {decision.reasoning_summary}"
    )


def audit_decision(decision, data_layer, policies: dict = None) -> AuditRecord:
    """
    Given a Decision object and the DataAccessLayer it was produced with,
    build a full AuditRecord: explanation + policy compliance check.
    """
    log_entries = [
        e for e in data_layer.get_log_for_customer(decision.customer_id)
        if e.agent_name == decision.agent_name
    ]
    fields_accessed = {e.field_accessed for e in log_entries}

    raw_violations = check_least_privilege(decision.agent_name, fields_accessed, policies=policies)
    # attach the specific customer_id to each violation for this decision
    violations = []
    for v in raw_violations:
        v.customer_id = decision.customer_id
        violations.append(v)

    explanation = build_plain_english_explanation(decision, decision.agent_name)

    return AuditRecord(
        agent_name=decision.agent_name,
        customer_id=decision.customer_id,
        decision=decision.decision,
        plain_english_explanation=explanation,
        fields_used=decision.fields_used,
        violations=violations,
    )


def audit_all(decisions: list, data_layer, policies: dict = None) -> list:
    return [audit_decision(d, data_layer, policies=policies) for d in decisions]


def summarize_violations(audit_records: list) -> dict:
    """Roll up violations across all decisions -- e.g. for a dashboard header."""
    total = 0
    by_agent = {}
    for record in audit_records:
        if record.violations:
            total += len(record.violations)
            by_agent[record.agent_name] = by_agent.get(record.agent_name, 0) + len(record.violations)
    return {"total_violations": total, "by_agent": by_agent}
