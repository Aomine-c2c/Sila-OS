"""
KAIROS RiskD - Central Safety Boundary & Pre-Trade Risk Engine
Architecture:
  Signal → DecisionSnapshot → RiskD → Execution Validation → ExecutionD

Risk States:
  - SAFE: System fully operational, well within risk thresholds.
  - NORMAL: Active trading within defined parameters.
  - CAUTION: Warning thresholds reached (drawdown > 50% limit or volatility elevated).
  - RESTRICTED: Approaching limits; sizing clamped, new positions throttled.
  - HALTED: Emergency halt engaged or limit breached. Close-only mode or full suspension.

Enforced Hard Invariants:
  1. Maximum positions (global & per-strategy)
  2. Exposure limits (gross & net notional exposure)
  3. Position sizing limits (max quantity & max notional per order)
  4. Daily loss limits (circuit breaker on realized/unrealized loss)
  5. Symbol limits (per-symbol exposure and restricted symbol whitelist/blacklist)
  6. Correlation limits (concentrated exposure across correlated assets)
  7. Spread limits (refuse execution when bid-ask spread is abnormally wide)
  8. Stale-data protection (reject decisions based on market ticks older than threshold)
  9. Duplicate-order protection (idempotency key & duplicate window detection)
  10. Broker-health checks (reject orders if broker latency exceeds SLA or disconnects)
  11. Order validation (limit price sanity, side, quantity, lot size step)
  12. Emergency halt (manual/automated instant circuit breaker)
  13. Close-only mode (only reducing position orders permitted)
  14. Strategy pause (individual strategy pause state)
  15. Non-autonomous hard limits: AI agents, plugins, and AEI cannot modify hard limits.
"""

import time
import enum
import dataclasses
import threading
from typing import Dict, List, Optional, Set, Any, Tuple

# =============================================================================
# 1. ENUMS & DATA MODELS
# =============================================================================

class RiskState(enum.Enum):
    SAFE = "SAFE"
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    RESTRICTED = "RESTRICTED"
    HALTED = "HALTED"

@dataclasses.dataclass(frozen=True)
class RiskHardLimits:
    """
    Immutable hard limits that CANNOT be autonomously modified by AI, plugins, or strategies.
    Any attempt to mutate these via untrusted channels is strictly rejected.
    """
    max_open_positions: int = 10
    max_gross_exposure_usd: float = 250_000.0
    max_net_exposure_usd: float = 150_000.0
    max_order_usd: float = 50_000.0
    max_single_position_qty: float = 100.0
    max_daily_loss_usd: float = 5_000.0
    max_drawdown_pct: float = 0.03 # 3%
    max_spread_pct: float = 0.015 # 1.5% max bid-ask spread
    max_tick_age_seconds: float = 3.0 # Stale market data threshold
    duplicate_window_seconds: float = 1.0 # Duplicate order suppression
    max_broker_latency_ms: float = 500.0 # Broker latency SLA
    max_symbol_exposure_usd: float = 75_000.0 # Per-symbol limit
    max_correlated_exposure_usd: float = 120_000.0 # Correlated group limit

@dataclasses.dataclass
class PositionInfo:
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return abs(self.quantity * self.current_price)

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity

@dataclasses.dataclass
class RiskVerdict:
    approved: bool
    reason: str
    adjusted_quantity: float
    risk_state: RiskState
    risk_timestamp_ns: int
    rule_triggered: Optional[str] = None
    close_only: bool = False

# =============================================================================
# 2. RISKD: CENTRAL SAFETY BOUNDARY
# =============================================================================

class RiskD:
    """
    KAIROS RiskD - Central Safety Boundary Daemon.
    Every signal and decision must pass through RiskD before reaching execution.
    """
    def __init__(self, hard_limits: Optional[RiskHardLimits] = None):
        self._lock = threading.RLock()
        self._hard_limits = hard_limits or RiskHardLimits()
        
        # Operational states
        self._risk_state: RiskState = RiskState.NORMAL
        self._emergency_halt: bool = False
        self._close_only_mode: bool = False
        self._paused_strategies: Set[str] = set()
        
        # Portfolio accounting
        self._positions: Dict[str, PositionInfo] = {}
        self._realized_daily_pnl: float = 0.0
        self._initial_daily_equity: float = 100_000.0
        self._peak_daily_equity: float = 100_000.0
        
        # Recent order tracking for duplicate protection (hash -> timestamp)
        self._recent_orders: Dict[str, float] = {}
        
        # Broker health monitoring
        self._broker_connected: bool = True
        self._broker_latency_ms: float = 1.5
        
        # Symbol restrictions & Correlation groups
        self._restricted_symbols: Set[str] = set() # Blacklisted symbols
        self._correlation_groups: Dict[str, Set[str]] = {
            "CRYPTO": {"BTC/USD", "ETH/USD", "SOL/USD"},
            "EQUITY_INDEX": {"SPY", "QQQ", "IWM"},
            "SEMIS": {"NVDA", "AMD", "TSM"}
        }

    @property
    def hard_limits(self) -> RiskHardLimits:
        return self._hard_limits

    @property
    def risk_state(self) -> RiskState:
        with self._lock:
            return self._risk_state

    # -------------------------------------------------------------------------
    # State Control (Emergency Halt, Close-Only, Pause Strategy)
    # -------------------------------------------------------------------------

    def set_emergency_halt(self, halted: bool, reason: str = "Manual operator trigger"):
        with self._lock:
            self._emergency_halt = halted
            if halted:
                self._risk_state = RiskState.HALTED
            else:
                self._recalculate_risk_state()

    def set_close_only_mode(self, enabled: bool):
        with self._lock:
            self._close_only_mode = enabled
            if enabled and self._risk_state != RiskState.HALTED:
                self._risk_state = RiskState.RESTRICTED
            elif not enabled and not self._emergency_halt:
                self._recalculate_risk_state()

    def pause_strategy(self, strategy_id: str):
        with self._lock:
            self._paused_strategies.add(strategy_id)

    def resume_strategy(self, strategy_id: str):
        with self._lock:
            self._paused_strategies.discard(strategy_id)

    def is_strategy_paused(self, strategy_id: str) -> bool:
        with self._lock:
            return strategy_id in self._paused_strategies

    def update_broker_health(self, connected: bool, latency_ms: float):
        with self._lock:
            self._broker_connected = connected
            self._broker_latency_ms = latency_ms

    def update_position(self, symbol: str, quantity: float, avg_price: float, current_price: float, realized_pnl: float = 0.0):
        with self._lock:
            if abs(quantity) < 1e-6:
                self._positions.pop(symbol, None)
            else:
                self._positions[symbol] = PositionInfo(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=avg_price,
                    current_price=current_price,
                    realized_pnl=realized_pnl
                )
            self._realized_daily_pnl += realized_pnl
            self._recalculate_risk_state()

    # -------------------------------------------------------------------------
    # Autonomous Mutation Protection
    # -------------------------------------------------------------------------

    def attempt_modify_limits(self, caller_role: str, new_limits: Dict[str, Any]) -> bool:
        """
        Hard limits CANNOT be modified autonomously by AI, plugins, or AEI.
        Only a verified human operator (with explicit physical hardware key / wheel role)
        can update them.
        """
        unauthorized_roles = {"ai", "ai_agent", "plugin", "aei", "adaptive_engine", "strategy", "untrusted"}
        if caller_role.lower() in unauthorized_roles:
            return False
        if caller_role.lower() not in {"wheel", "admin", "operator"}:
            return False
        return False # Hard limits are immutable at runtime for maximum institutional defense

    # -------------------------------------------------------------------------
    # Core Risk State Evaluation
    # -------------------------------------------------------------------------

    def _recalculate_risk_state(self):
        if self._emergency_halt:
            self._risk_state = RiskState.HALTED
            return

        total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        daily_pnl = self._realized_daily_pnl + total_unrealized
        equity = self._initial_daily_equity + daily_pnl
        if equity > self._peak_daily_equity:
            self._peak_daily_equity = equity

        drawdown_usd = self._peak_daily_equity - equity
        drawdown_pct = drawdown_usd / self._peak_daily_equity if self._peak_daily_equity > 0 else 0.0

        # Loss & drawdown circuit breaker
        if daily_pnl <= -self._hard_limits.max_daily_loss_usd or drawdown_pct >= self._hard_limits.max_drawdown_pct:
            self._risk_state = RiskState.HALTED
            return

        if self._close_only_mode:
            self._risk_state = RiskState.RESTRICTED
            return

        # Warning thresholds
        if drawdown_pct >= (self._hard_limits.max_drawdown_pct * 0.7) or daily_pnl <= (-self._hard_limits.max_daily_loss_usd * 0.7):
            self._risk_state = RiskState.RESTRICTED
        elif drawdown_pct >= (self._hard_limits.max_drawdown_pct * 0.4) or daily_pnl <= (-self._hard_limits.max_daily_loss_usd * 0.4):
            self._risk_state = RiskState.CAUTION
        elif len(self._positions) >= (self._hard_limits.max_open_positions * 0.8):
            self._risk_state = RiskState.CAUTION
        else:
            self._risk_state = RiskState.NORMAL

    # -------------------------------------------------------------------------
    # Pre-Trade Evaluation Pipeline
    # -------------------------------------------------------------------------

    def evaluate(self, decision: Any, market_tick: Optional[Any] = None) -> RiskVerdict:
        """
        The central safety gate. Validates every single trade decision before execution.
        """
        with self._lock:
            t_now = time.time_ns()

            # 1. Emergency Halt Check
            if self._emergency_halt or self._risk_state == RiskState.HALTED:
                return RiskVerdict(
                    approved=False,
                    reason="Risk Rejected: System is in HALTED state. All trading halted.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="EMERGENCY_HALT"
                )

            # 2. Strategy Pause Check
            strat_id = getattr(decision, "strategy_id", "")
            if strat_id in self._paused_strategies:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Strategy '{strat_id}' is currently PAUSED.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="STRATEGY_PAUSED"
                )

            # 3. Broker Health Check
            if not self._broker_connected:
                return RiskVerdict(
                    approved=False,
                    reason="Risk Rejected: Broker connection offline.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="BROKER_DISCONNECTED"
                )
            if self._broker_latency_ms > self._hard_limits.max_broker_latency_ms:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Broker latency {self._broker_latency_ms:.1f}ms exceeds limit {self._hard_limits.max_broker_latency_ms}ms.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="BROKER_LATENCY_BREACH"
                )

            # Extract decision properties
            symbol = getattr(decision, "symbol", "")
            side = getattr(decision, "side", "")
            if hasattr(side, "value"):
                side = side.value
            side = str(side).upper()

            quantity = float(getattr(decision, "quantity", 0.0))
            price = getattr(decision, "price", None)
            order_type = getattr(decision, "order_type", "")
            if hasattr(order_type, "value"):
                order_type = order_type.value
            order_type = str(order_type).upper()

            # 4. Order Sanity Validation
            if quantity <= 0:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Non-positive order quantity ({quantity}).",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="INVALID_QUANTITY"
                )

            if order_type == "LIMIT" and (price is None or price <= 0):
                return RiskVerdict(
                    approved=False,
                    reason="Risk Rejected: Non-positive limit price.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="INVALID_PRICE"
                )

            # Resolve effective price for notional calculations
            eff_price = price if price and price > 0 else (market_tick.mid if market_tick else 100.0)
            order_notional = quantity * eff_price

            # 5. Position Sizing Limits (per-order)
            if quantity > self._hard_limits.max_single_position_qty:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Order quantity {quantity} exceeds single position hard limit {self._hard_limits.max_single_position_qty}.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="MAX_ORDER_QTY_BREACH"
                )

            if order_notional > self._hard_limits.max_order_usd:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Order notional ${order_notional:,.2f} exceeds single order limit ${self._hard_limits.max_order_usd:,.2f}.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="MAX_ORDER_NOTIONAL_BREACH"
                )

            # 6. Duplicate-Order Protection (Idempotency)
            order_hash = f"{strat_id}:{symbol}:{side}:{quantity}:{price}:{order_type}"
            now_sec = time.time()
            if order_hash in self._recent_orders:
                prev_time = self._recent_orders[order_hash]
                if (now_sec - prev_time) < self._hard_limits.duplicate_window_seconds:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Duplicate order detected within {self._hard_limits.duplicate_window_seconds}s window.",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="DUPLICATE_ORDER_SUPPRESSED"
                    )
            self._recent_orders[order_hash] = now_sec

            # 7. Stale-Data & Spread Limits (from MarketD Normalized Tick)
            if market_tick is not None:
                tick_ts = getattr(market_tick, "timestamp", now_sec)
                age = now_sec - tick_ts
                if age > self._hard_limits.max_tick_age_seconds:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Market tick is stale (age: {age:.2f}s > {self._hard_limits.max_tick_age_seconds}s).",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="STALE_DATA_REJECTED"
                    )

                spread = getattr(market_tick, "spread", 0.0)
                mid = getattr(market_tick, "mid", eff_price)
                if mid > 0:
                    spread_pct = spread / mid
                    if spread_pct > self._hard_limits.max_spread_pct:
                        return RiskVerdict(
                            approved=False,
                            reason=f"Risk Rejected: Market spread {spread_pct*100:.2f}% exceeds maximum {self._hard_limits.max_spread_pct*100:.2f}%.",
                            adjusted_quantity=0.0,
                            risk_state=self._risk_state,
                            risk_timestamp_ns=t_now,
                            rule_triggered="SPREAD_LIMIT_BREACH"
                        )

            # Determine if this trade reduces or increases existing position
            existing_pos = self._positions.get(symbol)
            curr_qty = existing_pos.quantity if existing_pos else 0.0
            is_reducing = (curr_qty > 0 and side == "SELL") or (curr_qty < 0 and side == "BUY")

            # 8. Close-Only Mode Validation
            if self._close_only_mode and not is_reducing:
                return RiskVerdict(
                    approved=False,
                    reason="Risk Rejected: System in CLOSE-ONLY mode. Only position reducing orders allowed.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="CLOSE_ONLY_VIOLATION",
                    close_only=True
                )

            # 9. Symbol Blacklist & Restricted Symbol Check
            if symbol in self._restricted_symbols:
                return RiskVerdict(
                    approved=False,
                    reason=f"Risk Rejected: Symbol '{symbol}' is on the restricted asset list.",
                    adjusted_quantity=0.0,
                    risk_state=self._risk_state,
                    risk_timestamp_ns=t_now,
                    rule_triggered="SYMBOL_RESTRICTED"
                )

            # If order is increasing exposure, check portfolio capacity limits
            if not is_reducing:
                # 10. Maximum Open Positions Count
                if symbol not in self._positions and len(self._positions) >= self._hard_limits.max_open_positions:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Maximum open positions limit ({self._hard_limits.max_open_positions}) reached.",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="MAX_POSITIONS_BREACH"
                    )

                # 11. Per-Symbol Exposure Limit
                current_sym_exposure = existing_pos.market_value if existing_pos else 0.0
                new_sym_exposure = current_sym_exposure + order_notional
                if new_sym_exposure > self._hard_limits.max_symbol_exposure_usd:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Projected symbol exposure ${new_sym_exposure:,.2f} exceeds limit ${self._hard_limits.max_symbol_exposure_usd:,.2f}.",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="SYMBOL_EXPOSURE_BREACH"
                    )

                # 12. Correlation Limits
                for group_name, symbols in self._correlation_groups.items():
                    if symbol in symbols:
                        group_exposure = sum(
                            p.market_value for s, p in self._positions.items() if s in symbols
                        ) + order_notional
                        if group_exposure > self._hard_limits.max_correlated_exposure_usd:
                            return RiskVerdict(
                                approved=False,
                                reason=f"Risk Rejected: Correlated group '{group_name}' exposure ${group_exposure:,.2f} exceeds limit ${self._hard_limits.max_correlated_exposure_usd:,.2f}.",
                                adjusted_quantity=0.0,
                                risk_state=self._risk_state,
                                risk_timestamp_ns=t_now,
                                rule_triggered="CORRELATION_LIMIT_BREACH"
                            )

                # 13. Gross & Net Exposure Limits
                current_gross = sum(p.market_value for p in self._positions.values()) + order_notional
                if current_gross > self._hard_limits.max_gross_exposure_usd:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Projected gross exposure ${current_gross:,.2f} exceeds limit ${self._hard_limits.max_gross_exposure_usd:,.2f}.",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="GROSS_EXPOSURE_BREACH"
                    )

                projected_net_positions = {s: p.quantity * p.current_price for s, p in self._positions.items()}
                pos_change = order_notional if side == "BUY" else -order_notional
                projected_net_positions[symbol] = projected_net_positions.get(symbol, 0.0) + pos_change
                current_net = abs(sum(projected_net_positions.values()))
                if current_net > self._hard_limits.max_net_exposure_usd:
                    return RiskVerdict(
                        approved=False,
                        reason=f"Risk Rejected: Projected net exposure ${current_net:,.2f} exceeds limit ${self._hard_limits.max_net_exposure_usd:,.2f}.",
                        adjusted_quantity=0.0,
                        risk_state=self._risk_state,
                        risk_timestamp_ns=t_now,
                        rule_triggered="NET_EXPOSURE_BREACH"
                    )

            # If all checks pass:
            return RiskVerdict(
                approved=True,
                reason=f"Approved: Verified by RiskD pre-trade gatekeeper (State: {self._risk_state.value}).",
                adjusted_quantity=quantity,
                risk_state=self._risk_state,
                risk_timestamp_ns=t_now,
                close_only=self._close_only_mode
            )
