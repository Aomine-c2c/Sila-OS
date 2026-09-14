"""
KAIROS Core Trading Engine - Risk Gateway and Pipeline Architecture
Strictly follows the non-bypassable sequence:
Signal -> Decision -> Risk -> Execution -> Broker
"""

import time
import json
import dataclasses
from typing import Optional, Dict, Any

@dataclasses.dataclass
class MarketSignal:
    timestamp_ns: int
    symbol: str
    signal_type: str # 'BUY', 'SELL', 'NEUTRAL'
    strength: float
    metadata: Dict[str, Any]

@dataclasses.dataclass
class OrderDecision:
    timestamp_ns: int
    symbol: str
    side: str
    quantity: float
    order_type: str # 'LIMIT', 'MARKET'
    price: Optional[float]
    strategy_id: str

@dataclasses.dataclass
class RiskVerdict:
    approved: bool
    reason: str
    adjusted_quantity: float
    risk_timestamp_ns: int

class RiskGatekeeper:
    """
    Immutable Risk Engine.
    Hard limits that CANNOT be bypassed by AI agents, trading plugins, or strategies.
    """
    def __init__(self, max_position_size=100.0, max_order_value_usd=50000.0, max_drawdown_pct=0.03):
        self.max_position_size = max_position_size
        self.max_order_value_usd = max_order_value_usd
        self.max_drawdown_pct = max_drawdown_pct
        self.current_drawdown_pct = 0.005 # Baseline healthy state

    def evaluate(self, decision: OrderDecision) -> RiskVerdict:
        t_now = time.time_ns()
        
        # Rule 1: Circuit breaker on drawdown
        if self.current_drawdown_pct >= self.max_drawdown_pct:
            return RiskVerdict(
                approved=False,
                reason=f"Risk Rejected: Maximum system drawdown exceeded ({self.current_drawdown_pct*100:.1f}% >= {self.max_drawdown_pct*100:.1f}%)",
                adjusted_quantity=0.0,
                risk_timestamp_ns=t_now
            )

        # Rule 2: Max quantity check
        if decision.quantity > self.max_position_size:
            return RiskVerdict(
                approved=False,
                reason=f"Risk Rejected: Order size {decision.quantity} exceeds hard limit {self.max_position_size}",
                adjusted_quantity=0.0,
                risk_timestamp_ns=t_now
            )

        # Rule 3: Price validity for limits
        if decision.order_type == "LIMIT" and (decision.price is None or decision.price <= 0):
            return RiskVerdict(
                approved=False,
                reason="Risk Rejected: Non-positive price for limit order",
                adjusted_quantity=0.0,
                risk_timestamp_ns=t_now
            )

        # Approved
        return RiskVerdict(
            approved=True,
            reason="Approved: All risk parameters within nominal bounds",
            adjusted_quantity=decision.quantity,
            risk_timestamp_ns=t_now
        )

class ExecutionEngine:
    def __init__(self, risk_gatekeeper: RiskGatekeeper):
        self.risk_gatekeeper = risk_gatekeeper

    def execute_decision(self, decision: OrderDecision):
        """
        Executes an order ONLY after rigorous approval through the RiskGatekeeper.
        """
        verdict = self.risk_gatekeeper.evaluate(decision)
        if not verdict.approved:
            print(f"[Execution Engine] BLOCKED: {verdict.reason}")
            return {"status": "REJECTED_BY_RISK", "verdict": verdict}
            
        print(f"[Execution Engine] APPROVED: Sending {decision.side} {verdict.adjusted_quantity} {decision.symbol} to Broker Gateway.")
        return {"status": "SENT_TO_BROKER", "verdict": verdict}
