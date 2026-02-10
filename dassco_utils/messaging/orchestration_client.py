from __future__ import annotations
import uuid
import traceback
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict
from .async_rabbitmq_client import AsyncRabbitMqClient

logger = logging.getLogger(__name__)

@dataclass
class Asset:
    id: str
    info: Dict[str, Any]

@dataclass
class OrchestrationEvent:
    run_id: uuid.UUID
    idx: int
    event: str
    params: Dict[str, Any]
    asset: Asset
    reply_queue: str

class OrchestrationClient:
    """
    Helper for microservices to communicate with the Orchestrator
    :param mq_client: An initialized AsyncRabbitMqClient class
    :param service_name: The name of the service (default: unknown-service)
    """
    def __init__(self, mq_client: AsyncRabbitMqClient, service_name: str = "unknown-service") -> None:
        self._mq = mq_client
        self._service_name = service_name
        self._handlers: Dict[str, Callable[[OrchestrationEvent], Awaitable[Dict[str, Any]]]] = {}

    def handler(self, event_name: str):
        """
        Decorator to register event handler
        :param event_name: The name of the event to handle
        """
        def decorator(func: Callable[[OrchestrationEvent], Awaitable[Dict[str, Any]]]):
            self._handlers[event_name] = func
            return func
        return decorator

    async def register_handlers(self) -> None:
        """ Register all decorated handlers with the RabbitMq client"""
        for event_name, func in self._handlers.items():
            await self._mq.add_handler(event_name, handler=await self._create_wrapper(func))

    async def _create_wrapper(self, func: Callable):
        async def wrapper(payload: Dict[str, Any], msg_props):
            evt = await self._parse_event(payload)
            if evt is None:
                return

            retry_count = self._get_retry_count(msg_props)
            evt.params["retry_count"] = retry_count
            if self._is_max_retries_exceeded(retry_count):
                self._log(f"Exceeded maximum number of retries in '{evt.run_id}':'{evt.event}'", "ERROR")
                await self._send_response(
                    evt,
                    status="FAILED",
                    result={
                        "error": "Max retries exceeded",
                        "reason": f"Failed after {retry_count} retry attempts"
                    }
                )
                return

            try:
                result = await func(evt)
                await self._send_response(evt, status="DONE", result=result)
            except Exception as e:
                await self._handle_error(evt, e)
        return wrapper

    @classmethod
    def _get_retry_count(cls, msg_props) -> int:
        """Get retry count from message headers"""
        if hasattr(msg_props, "headers") and msg_props.headers:
            return msg_props.headers.get("x-retry-count", 0)
        return 0

    def _is_max_retries_exceeded(self, retry_count: int) -> bool:
        """Check if the retry count has exceeded maximum retries"""
        max_retries = len(self._mq.get_retry_config().retry_delays)
        return retry_count >= max_retries

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if the exception is retryable according to the RabbitMQ configuration"""
        return isinstance(exception, self._mq.get_retry_config().retryable_exceptions)

    async def _handle_error(self, evt: OrchestrationEvent, error: Exception) -> None:
        if self._is_retryable(error):
            raise
        else:
            self._log(f"Fatal error in '{evt.run_id}':'{evt.event}': {type(error).__name__}: {error}", "ERROR")
            await self._send_response(
                evt,
                status="FAILED",
                result={
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                },
            )

    async def _parse_event(self, payload: Dict[str, Any]):
        try:
            return OrchestrationEvent(
                run_id=uuid.UUID(payload["run_id"]),
                idx=int(payload["idx"]),
                event=payload["event"],
                params=payload["params"],
                asset=Asset(**payload["asset"]),
                reply_queue=payload["reply_queue"],
            )
        except Exception as e:
            payload_response = {
                'run_id': payload.get("run_id", ""),
                'idx': payload.get("idx", -1),
                'event': payload.get("event", ""),
                'status': "FAILED",
                "result": {
                    'error': 'Invalid payload format',
                    'details': str(e)
                }
            }
            reply_queue = payload.get("reply_queue")
            if reply_queue:
                await self._mq.publish(reply_queue, payload_response)
            return None

    async def _send_response(
        self,
        evt: OrchestrationEvent,
        status: str,
        result: Dict[str, Any],
    ) -> None:
        """ Send response to the Orchestrator """
        payload = {
            "run_id": str(evt.run_id),
            "idx": evt.idx,
            "event": evt.event,
            "status": status,
            "result": result,
        }
        await self._mq.publish(evt.reply_queue, payload)
        self._log(f"Sent response: {payload}", "DEBUG")

    def _log(self, message: str, level: str) -> None:
        lvl = logging._nameToLevel.get(level.upper(), logging.INFO)
        logger.log(lvl, "[%s] %s", self._service_name, message)