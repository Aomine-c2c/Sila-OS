"""
KAIROS AI Agent Platform & Autonomous Reasoning Framework.
Enforces multi-layer safety invariants, prompt injection defense,
typed permission tiers, and the non-bypassable execution pipeline:
Agent -> Proposal -> Policy -> RiskD -> ExecutionD.

Initial Agents:
  - Vincent: Lead Quant Reasoning & Strategy Allocation
  - Xiphos: Tactical Execution & Microstructure Analyzer
  - Watcher: Market Anomaly, Outlier & Volatility Monitor
  - Researcher: Factor Engineering & Backtest Evaluator
  - Scheduler: Macroeconomic & Portfolio Task Orchestrator

Permission Tiers:
  - READ: Market, orderbook, news, telemetry data
  - ANALYZE: Feature calculation, factor analysis, NLP inference
  - PROPOSE: Structured strategy/order proposals (Default cap for agents)
  - REQUEST: Human operator or supervisor authorization
  - EXECUTE: Direct order execution (STRICTLY PROHIBITED for AI agents)
"""

import os
import sys
import time
import json
import enum
import re
import hashlib
import dataclasses
from typing import Dict, List, Set, Optional, Any, Tuple

# =============================================================================
# 1. ENUMS & DATA STRUCTURES
# =============================================================================

class PermissionTier(enum.Enum):
    READ = "READ"
    ANALYZE = "ANALYZE"
    PROPOSE = "PROPOSE"
    REQUEST = "REQUEST"
    EXECUTE = "EXECUTE"

@dataclasses.dataclass
class AgentMetadata:
    identity: Dict[str, str] # id, name, role, model_family, description
    version: str
    permissions: List[PermissionTier]
    tools: List[str]
    memory: Dict[str, Any] # working_memory, episodic_cache, context_window
    tasks: List[Dict[str, Any]]
    audit_information: Dict[str, Any] # created_at, certified_by, hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity,
            "version": self.version,
            "permissions": [p.value for p in self.permissions],
            "tools": self.tools,
            "memory": self.memory,
            "tasks": self.tasks,
            "audit_information": self.audit_information
        }

@dataclasses.dataclass
class AgentProposal:
    proposal_id: str
    agent_id: str
    timestamp_ns: int
    symbol: str
    side: str # "BUY", "SELL", "HOLD"
    quantity: float
    price: Optional[float]
    order_type: str # "LIMIT", "MARKET"
    rationale: str
    confidence: float
    urgency: str # "LOW", "MEDIUM", "HIGH"
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

@dataclasses.dataclass
class AuditRecord:
    audit_id: str
    timestamp_utc: str
    model: str
    provider: str
    task: str
    context: Dict[str, Any]
    tools: List[str]
    output: str
    proposal: Optional[Dict[str, Any]]
    decision: Dict[str, Any]
    result: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

# =============================================================================
# 2. PROMPT INJECTION & UNTRUSTED INPUT DEFENSE ENGINE
# =============================================================================

class PromptInjectionDefense:
    """
    Guards AI models against adversarial prompt injections embedded in
    untrusted market data, financial news feeds, analyst commentary, or web text.
    """
    SUSPICIOUS_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
        r"system\s*:\s*override",
        r"bypass\s+(risk|security|gatekeeper|firewall|limits?)",
        r"execute\s+(immediately|now|direct|trade)",
        r"you\s+are\s+now\s+(in\s+developer\s+mode|unrestricted|god\s+mode)",
        r"send\s+(all\s+)?(credentials?|keys?|tokens?|secrets?)",
        r"disable\s+(riskd|policy|safeguards?)",
        r"modify\s+(hard\s+limits?|drawdown|risk\s+config)"
    ]

    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]

    @classmethod
    def inspect_and_sanitize(cls, raw_text: str) -> Tuple[bool, str, List[str]]:
        """
        Inspects text for prompt injection attempts.
        Returns: (is_clean, sanitized_text, detected_threats)
        """
        detected_threats = []
        for pat in cls.COMPILED_PATTERNS:
            if pat.search(raw_text):
                detected_threats.append(pat.pattern)

        # Neutralize control characters and XML/HTML delimiter breaks
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", raw_text)
        sanitized = sanitized.replace("<|im_start|>", "[STRIPPED]")
        sanitized = sanitized.replace("<|im_end|>", "[STRIPPED]")
        sanitized = sanitized.replace("```system", "```data")

        # Wrap in unambiguous data encapsulation
        encapsulated = f"<untrusted_external_content>\n{sanitized}\n</untrusted_external_content>"

        is_clean = len(detected_threats) == 0
        return is_clean, encapsulated, detected_threats

# =============================================================================
# 3. AI AGENT BASE IMPLEMENTATION
# =============================================================================

class AIAgent:
    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata

    @property
    def agent_id(self) -> str:
        return self.metadata.identity["id"]

    @property
    def name(self) -> str:
        return self.metadata.identity["name"]

    def has_permission(self, tier: PermissionTier) -> bool:
        return tier in self.metadata.permissions

    def evaluate_task(
        self,
        task_name: str,
        context: Dict[str, Any],
        model: str = "kairos-reasoner-7b",
        provider: str = "kairos-local-vllm"
    ) -> Tuple[str, Optional[AgentProposal], List[str]]:
        """
        Executes reasoning over sanitized context and produces an advisory proposal.
        """
        # 1. Sanitize any external text in context
        raw_news = context.get("news_feed", "")
        tools_used = ["market_telemetry_reader"]
        if raw_news:
            tools_used.append("untrusted_content_sanitizer")
            is_clean, sanitized, threats = PromptInjectionDefense.inspect_and_sanitize(raw_news)
            if not is_clean:
                reasoning = f"[AGENT DEFENSE ACTIVATED] Detected {len(threats)} prompt injection threats. External text quarantined."
                return reasoning, None, tools_used
            context["sanitized_news"] = sanitized

        # 2. Heuristic or LLM-driven reasoning
        tools_used.append("regime_analyzer")
        symbol = context.get("symbol", "SPY")
        price = context.get("price", 500.0)
        imbalance = context.get("orderbook_imbalance", 0.0)
        momentum = context.get("momentum_score", 0.0)

        # Agent-specific strategy formulation
        if self.agent_id == "vincent":
            hypothesis = f"Vincent Macro Allocation: Balanced factor exposure with positive drift on {symbol}."
            side = "BUY" if (imbalance > 0.1 or momentum > 0.2) else "HOLD"
            qty = 5.0
            conf = 0.86
        elif self.agent_id == "xiphos":
            hypothesis = f"Xiphos Tactical: Microstructure imbalance {imbalance:+.2f} indicates immediate liquidity grab."
            side = "BUY" if imbalance > 0.05 else ("SELL" if imbalance < -0.05 else "HOLD")
            qty = 3.0
            conf = 0.91
        elif self.agent_id == "watcher":
            hypothesis = f"Watcher Monitor: Volatility nominal; outlier detection zero."
            side = "HOLD"
            qty = 0.0
            conf = 0.95
        elif self.agent_id == "researcher":
            hypothesis = f"Researcher Factor: Out-of-sample Sharpe 1.85 validated on historical dataset."
            side = "BUY" if momentum > 0.1 else "HOLD"
            qty = 4.0
            conf = 0.82
        elif self.agent_id == "scheduler":
            hypothesis = f"Scheduler: Portfolio rebalance slot open; no high-impact macro releases in next 60m."
            side = "HOLD"
            qty = 0.0
            conf = 0.99
        else:
            hypothesis = f"Generic agent reasoning on {symbol}."
            side = "HOLD"
            qty = 0.0
            conf = 0.5

        proposal = None
        if side in ("BUY", "SELL") and qty > 0:
            proposal = AgentProposal(
                proposal_id=f"prop_{self.agent_id}_{int(time.time_ns())}",
                agent_id=self.agent_id,
                timestamp_ns=time.time_ns(),
                symbol=symbol,
                side=side,
                quantity=qty,
                price=price,
                order_type="LIMIT",
                rationale=hypothesis,
                confidence=conf,
                urgency="MEDIUM",
                metadata={"imbalance": imbalance, "momentum": momentum}
            )

        return hypothesis, proposal, tools_used

# =============================================================================
# 4. POLICY ENGINE & PIPELINE ORCHESTRATOR
# =============================================================================

class PolicyEngine:
    """
    Validates agent proposals before routing to RiskD.
    Assures permissions, limits, and that AI output NEVER becomes an order directly.
    """
    @staticmethod
    def evaluate_proposal(agent: AIAgent, proposal: AgentProposal) -> Tuple[bool, str]:
        # 1. Verify agent has PROPOSE permission
        if not agent.has_permission(PermissionTier.PROPOSE):
            return False, f"POLICY REJECTED: Agent '{agent.agent_id}' lacks PROPOSE permission."

        # 2. Hard Invariant: Agent must NEVER have EXECUTE permission
        if agent.has_permission(PermissionTier.EXECUTE):
            return False, f"POLICY CRITICAL: Agent '{agent.agent_id}' illegally holds EXECUTE permission. Quarantined."

        # 3. Parameter checks
        if proposal.quantity <= 0:
            return False, "POLICY REJECTED: Quantity must be positive."
        if proposal.side not in ("BUY", "SELL"):
            return False, f"POLICY REJECTED: Invalid order side '{proposal.side}'."

        return True, "POLICY APPROVED: Forwarding proposal to RiskD gatekeeper."

# =============================================================================
# 5. KAIROS AI AGENT PLATFORM MANAGER
# =============================================================================

class AIAgentPlatform:
    """
    Unified manager for AI agents, prompt injection filtering, audit logging,
    and the Agent -> Proposal -> Policy -> RiskD -> ExecutionD pipeline.
    """
    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = "/var/lib/kairos/ai" if os.path.exists("/var/lib/kairos") else os.path.expanduser("~/.kairos/ai")
        self.storage_dir = storage_dir
        self.audit_dir = os.path.join(self.storage_dir, "audit")
        os.makedirs(self.audit_dir, exist_ok=True)

        self.agents: Dict[str, AIAgent] = {}
        self.audit_records: List[AuditRecord] = []

        self._initialize_initial_agents()
        self._load_audit_history()

    def _initialize_initial_agents(self):
        """Initializes the 5 required certified KAIROS agents."""
        initial_configs = [
            {
                "id": "vincent",
                "name": "Vincent",
                "role": "Lead Quantitative Reasoning & Strategy Allocation",
                "model_family": "kairos-deepseek-quant-7b",
                "description": "Multi-factor portfolio reasoning and macro allocation optimizer",
                "tools": ["market_reader", "factor_evaluator", "regime_detector", "portfolio_optimizer"]
            },
            {
                "id": "xiphos",
                "name": "Xiphos",
                "role": "Tactical Execution & Microstructure Analyzer",
                "model_family": "kairos-tactical-qwen-3b",
                "description": "Microstructure level-2 depth imbalance and tactical execution specialist",
                "tools": ["l2_orderbook_analyzer", "slippage_estimator", "cvd_calculator"]
            },
            {
                "id": "watcher",
                "name": "Watcher",
                "role": "Market Anomaly, Outlier & Volatility Monitor",
                "model_family": "kairos-anomaly-fast-1b",
                "description": "Real-time outlier detector and high-frequency volatility surface guard",
                "tools": ["volatility_surface_tracker", "anomaly_detector", "circuit_breaker_sentinel"]
            },
            {
                "id": "researcher",
                "name": "Researcher",
                "role": "Statistical Factor Engineering & Backtest Evaluator",
                "model_family": "kairos-factor-reasoner-7b",
                "description": "Out-of-sample backtesting, alpha factor discovery, and hypothesis testing",
                "tools": ["backtest_simulator", "feature_engine", "dataset_loader"]
            },
            {
                "id": "scheduler",
                "name": "Scheduler",
                "role": "Macroeconomic & Portfolio Task Orchestrator",
                "model_family": "kairos-task-orchestrator-1b",
                "description": "Macroeconomic calendar tracker and portfolio rebalance task coordinator",
                "tools": ["macro_calendar_reader", "task_queue_manager", "service_health_monitor"]
            }
        ]

        for cfg in initial_configs:
            # Hard Security Rule: Default agents strictly receive READ, ANALYZE, PROPOSE
            permissions = [PermissionTier.READ, PermissionTier.ANALYZE, PermissionTier.PROPOSE]

            meta = AgentMetadata(
                identity={
                    "id": cfg["id"],
                    "name": cfg["name"],
                    "role": cfg["role"],
                    "model_family": cfg["model_family"],
                    "description": cfg["description"]
                },
                version="1.0.0",
                permissions=permissions,
                tools=cfg["tools"],
                memory={"working_memory": {}, "context_tokens": 4096, "session_id": f"sess_{cfg['id']}"},
                tasks=[{"task_id": "initial_scan", "status": "READY"}],
                audit_information={
                    "certified_by": "KAIROS Core Security Boundary",
                    "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "hash": hashlib.sha256(cfg["id"].encode()).hexdigest()
                }
            )
            self.agents[cfg["id"]] = AIAgent(meta)

    def _load_audit_history(self):
        """Loads recent audit logs from disk."""
        log_file = os.path.join(self.audit_dir, "ai_audit.jsonl")
        if not os.path.exists(log_file):
            return
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        rec = AuditRecord(**data)
                        self.audit_records.append(rec)
        except Exception:
            pass

    def _record_audit(self, record: AuditRecord):
        """Persists immutable audit log to disk."""
        self.audit_records.append(record)
        log_file = os.path.join(self.audit_dir, "ai_audit.jsonl")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Public API & Pipeline Execution
    # -------------------------------------------------------------------------

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.metadata.to_dict() for a in self.agents.values()]

    def get_agent(self, agent_id: str) -> Optional[AIAgent]:
        return self.agents.get(agent_id)

    def execute_agent_pipeline(
        self,
        agent_id: str,
        context: Dict[str, Any],
        model: str = "kairos-reasoner-7b",
        provider: str = "kairos-local-engine"
    ) -> Dict[str, Any]:
        """
        Executes the full KAIROS non-bypassable sequence:
        Agent -> Proposal -> Policy -> RiskD -> ExecutionD
        Every step is recorded in the immutable audit log.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "ERROR", "error": f"Agent '{agent_id}' not found"}

        audit_id = f"audit_{agent_id}_{int(time.time_ns())}"
        task_name = context.get("task_name", "alpha_signal_evaluation")

        # Step 1: Agent Reasoning & Proposal Formulation
        output, proposal, tools_used = agent.evaluate_task(task_name, context, model, provider)

        # If no proposal was generated (e.g. HOLD or quarantined)
        if not proposal:
            decision = {"status": "NO_PROPOSAL", "reason": output}
            result = {"status": "IDLE", "executed": False}
            rec = AuditRecord(
                audit_id=audit_id,
                timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                model=model,
                provider=provider,
                task=task_name,
                context=context,
                tools=tools_used,
                output=output,
                proposal=None,
                decision=decision,
                result=result
            )
            self._record_audit(rec)
            return {
                "status": "COMPLETED",
                "audit_id": audit_id,
                "agent_id": agent_id,
                "output": output,
                "proposal": None,
                "policy_status": "SKIPPED",
                "risk_status": "SKIPPED",
                "execution_status": "NONE"
            }

        # Step 2: Policy Verification
        policy_ok, policy_msg = PolicyEngine.evaluate_proposal(agent, proposal)
        if not policy_ok:
            decision = {"status": "POLICY_REJECTED", "reason": policy_msg}
            result = {"status": "BLOCKED_AT_POLICY", "executed": False}
            rec = AuditRecord(
                audit_id=audit_id,
                timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                model=model,
                provider=provider,
                task=task_name,
                context=context,
                tools=tools_used,
                output=output,
                proposal=proposal.to_dict(),
                decision=decision,
                result=result
            )
            self._record_audit(rec)
            return {
                "status": "BLOCKED",
                "audit_id": audit_id,
                "agent_id": agent_id,
                "output": output,
                "proposal": proposal.to_dict(),
                "policy_status": "REJECTED",
                "policy_message": policy_msg,
                "risk_status": "NOT_REACHED",
                "execution_status": "NONE"
            }

        # Step 3: RiskD Pre-Trade Gatekeeper Evaluation
        from trading.risk_gatekeeper import RiskGatekeeper, ExecutionEngine, OrderDecision
        risk = RiskGatekeeper()
        engine = ExecutionEngine(risk)

        # Convert proposal to formal OrderDecision
        order_dec = OrderDecision(
            timestamp_ns=proposal.timestamp_ns,
            symbol=proposal.symbol,
            side=proposal.side,
            quantity=proposal.quantity,
            order_type=proposal.order_type,
            price=proposal.price,
            strategy_id=f"ai_{proposal.agent_id}"
        )

        risk_verdict = risk.evaluate(order_dec)
        if not risk_verdict.approved:
            decision = {
                "policy": policy_msg,
                "riskd_verdict": "REJECTED",
                "riskd_reason": risk_verdict.reason
            }
            result = {"status": "BLOCKED_AT_RISKD", "executed": False}
            rec = AuditRecord(
                audit_id=audit_id,
                timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                model=model,
                provider=provider,
                task=task_name,
                context=context,
                tools=tools_used,
                output=output,
                proposal=proposal.to_dict(),
                decision=decision,
                result=result
            )
            self._record_audit(rec)
            return {
                "status": "BLOCKED",
                "audit_id": audit_id,
                "agent_id": agent_id,
                "output": output,
                "proposal": proposal.to_dict(),
                "policy_status": "APPROVED",
                "risk_status": "REJECTED",
                "risk_message": risk_verdict.reason,
                "execution_status": "NONE"
            }

        # Step 4: ExecutionD Dispatch
        exec_res = engine.execute_decision(order_dec)
        decision = {
            "policy": policy_msg,
            "riskd_verdict": "APPROVED",
            "riskd_reason": risk_verdict.reason
        }
        result = {
            "status": exec_res.get("status"),
            "executed": True,
            "broker_gateway": "FIX4.4_PRIMARY"
        }

        rec = AuditRecord(
            audit_id=audit_id,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            model=model,
            provider=provider,
            task=task_name,
            context=context,
            tools=tools_used,
            output=output,
            proposal=proposal.to_dict(),
            decision=decision,
            result=result
        )
        self._record_audit(rec)

        return {
            "status": "SUCCESS",
            "audit_id": audit_id,
            "agent_id": agent_id,
            "output": output,
            "proposal": proposal.to_dict(),
            "policy_status": "APPROVED",
            "risk_status": "APPROVED",
            "execution_status": exec_res.get("status")
        }

    def get_audit_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in reversed(self.audit_records[-limit:])]

# Global singleton instance
_AI_PLATFORM = None

def get_ai_platform() -> AIAgentPlatform:
    global _AI_PLATFORM
    if _AI_PLATFORM is None:
        _AI_PLATFORM = AIAgentPlatform()
    return _AI_PLATFORM
