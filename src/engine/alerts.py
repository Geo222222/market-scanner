"""Rules engine and signal publishing for scalper alerts."""
from __future__ import annotations

import asyncio
import ast
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore

from ..config import get_settings

LOGGER = logging.getLogger(__name__)

_ALLOWED_VARIABLES = {
    "rank",
    "score",
    "liquidity_edge",
    "momentum_edge",
    "volatility_edge",
    "microstructure_edge",
    "anomaly_residual",
    "manipulation_score",
}

_ALLOWED_COMPARE_OPS = (ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.In, ast.NotIn)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub, ast.Not)
_UNSAFE_NODES = (
    ast.Call,
    ast.Attribute,
    ast.Subscript,
    ast.Lambda,
    ast.Dict,
    ast.ListComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
    ast.NamedExpr,
)


def _compile_rule_expression(expression: str) -> object:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - invalid rule
        raise ValueError(f"invalid syntax: {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, _UNSAFE_NODES):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in _ALLOWED_VARIABLES:
            raise ValueError(f"unknown identifier '{node.id}'")
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if not isinstance(op, _ALLOWED_COMPARE_OPS):
                    raise ValueError(f"unsupported comparison operator '{type(op).__name__}'")
        if isinstance(node, ast.BinOp) and not isinstance(node.op, _ALLOWED_BIN_OPS):
            raise ValueError(f"unsupported operator '{type(node.op).__name__}'")
        if isinstance(node, ast.BoolOp) and not isinstance(node.op, _ALLOWED_BOOL_OPS):
            raise ValueError(f"unsupported boolean operator '{type(node.op).__name__}'")
        if isinstance(node, ast.UnaryOp) and not isinstance(node.op, _ALLOWED_UNARY_OPS):
            raise ValueError(f"unsupported unary operator '{type(node.op).__name__}'")
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool, str, type(None))):
                continue
            raise ValueError(f"unsupported constant type '{type(node.value).__name__}'")
    return compile(tree, "<alert_rule>", "eval")


@dataclass(slots=True)
class AlertRule:
    """In-memory representation of a user-defined alert rule."""

    name: str
    expression: str
    scope: str = "*"
    _code: object | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        try:
            self._code = _compile_rule_expression(self.expression)
        except ValueError as exc:  # pragma: no cover - invalid rule guard
            LOGGER.warning("Rule %s disabled: %s", self.name, exc)
            self._code = None

    def matches(self, context: Dict[str, Any]) -> bool:
        if self._code is None:
            return False
        allowed_names = {key: context.get(key) for key in _ALLOWED_VARIABLES}
        try:
            return bool(eval(self._code, {"__builtins__": {}}, allowed_names))
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Rule %s evaluation failed: %s", self.name, exc)
            return False


class SignalBus:
    """Redis backed signal publisher with in-memory fallback for tests."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Any | None = None
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._publisher_started = False
        self.rules: List[AlertRule] = []

    async def ensure_client(self) -> None:
        if redis is None or not self._settings.redis_url:
            return
        if self._client is None:
            self._client = redis.from_url(self._settings.redis_url)
        if not self._publisher_started:
            asyncio.create_task(self._publisher())
            self._publisher_started = True

    async def _publisher(self) -> None:
        while True:
            payload = await self._queue.get()
            if self._client is None:
                LOGGER.debug("Signal: %s", payload)
                await self._send_webhook(payload)
                continue
            try:
                await self._client.publish(self._settings.signal_channel, json.dumps(payload))
                await self._send_webhook(payload)
            except Exception as exc:  # pragma: no cover - network failure
                LOGGER.warning("Redis publish failed: %s", exc)

    async def publish_if_matched(self, symbol_payload: Dict[str, Any]) -> None:
        symbol = symbol_payload.get("symbol")
        for rule in list(self.rules):
            if rule.scope not in ("*", symbol):
                continue
            if rule.matches(symbol_payload):
                await self.enqueue_signal({"rule": rule.name, "symbol": symbol, "payload": symbol_payload})

    async def enqueue_signal(self, payload: Dict[str, Any]) -> None:
        await self.ensure_client()
        await self._queue.put(payload)

    def register_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def clear_rules(self) -> None:
        self.rules.clear()

    async def _send_webhook(self, payload: Dict[str, Any]) -> None:
        if not getattr(self._settings, "alert_webhook_url", None):
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self._settings.alert_webhook_url, json=payload)
        except Exception as exc:  # pragma: no cover
            LOGGER.debug("Webhook post failed: %s", exc)

_signal_bus: SignalBus | None = None


def get_signal_bus() -> SignalBus:
    global _signal_bus
    if _signal_bus is None:
        _signal_bus = SignalBus()
    return _signal_bus
