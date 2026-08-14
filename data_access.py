"""
data_access.py
---------------
This is the key architectural piece: agents never read customer records
directly. They go through a DataAccessLayer, which logs exactly which
fields each agent read, for which customer, at what time.

This is what makes real auditing possible -- in a real bank, this would
be the layer instrumented around your feature store / data warehouse
queries, not something bolted on after the fact.

Every read is recorded as an AccessLogEntry, which the governance agent
later uses to:
  1. Check field-level access against each agent's declared policy scope
  2. Reconstruct which specific data points fed into a decision
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AccessLogEntry:
    timestamp: str
    agent_name: str
    customer_id: str
    field_accessed: str
    value_read: Any


class DataAccessLayer:
    def __init__(self, customers: list):
        # index customers by id for fast lookup
        self._customers = {c["customer_id"]: c for c in customers}
        self.access_log: list[AccessLogEntry] = []

    def read_field(self, agent_name: str, customer_id: str, field_name: str):
        """The ONLY way an agent may read customer data. Every call is logged."""
        record = self._customers.get(customer_id)
        if record is None:
            raise KeyError(f"Unknown customer_id: {customer_id}")
        if field_name not in record:
            raise KeyError(f"Unknown field: {field_name}")

        value = record[field_name]
        self.access_log.append(AccessLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_name=agent_name,
            customer_id=customer_id,
            field_accessed=field_name,
            value_read=value,
        ))
        return value

    def get_log_for_customer(self, customer_id: str) -> list:
        return [e for e in self.access_log if e.customer_id == customer_id]

    def get_log_for_agent(self, agent_name: str) -> list:
        return [e for e in self.access_log if e.agent_name == agent_name]
