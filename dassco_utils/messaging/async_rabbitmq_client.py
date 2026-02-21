import asyncio
import json
from typing import Callable, Optional, Dict
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractConnection, AbstractIncomingMessage, ExchangeType
from .exceptions import TransientError, ExpectedRetry

class ConnectionOptions(object):
    """Configuration options for RabbitMQ client"""
    host_name: str = 'localhost'
    username: str = 'guest'
    password: str = 'guest'
    enable_tls: bool = False

class RetryConfig(object):
    """
    Retry configuration behaviour

    By default, a message is retried 5 times:
        First after 5 seconds, then 30 seconds, then 2 minutes, then 10 minutes, and finally 30 minutes.
    """
    retry_delays: list = [5000, 30000, 120000, 600000, 1800000]  # 5s, 30s, 2m, 10m, 30m
    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        TransientError,
        ExpectedRetry
    )

    @classmethod
    def format_delay(cls, ms: int) -> str:
        """Format the retry delay in human-readable format"""
        seconds = ms / 1000
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"
        else:
            return f"{seconds/3600:.1f} hours"


class AsyncRabbitMqClient:
    def __init__(self, options: ConnectionOptions = None, retry_config = None):
        """
        Initialize an asynchronous RabbitMQ client
        :param options: connection options (if None, defaults are used)
        :param retry_config: retry configuration (if None, defaults are used)
        """
        self._options = options if options else ConnectionOptions()
        self._retry_config = retry_config if retry_config else RetryConfig()
        self._consumer_connection = None
        self._producer = None
        self._consumers = []

    async def _create_connection(self) -> AbstractConnection:
        """
        Create a robust RabbitMQ connection
        """
        url = f"amqp://{self._options.username}:{self._options.password}@{self._options.host_name}/"
        connection = await connect_robust(url)
        return connection

    def get_retry_config(self) -> RetryConfig:
        """ Get the retry configuration """
        return self._retry_config

    async def publish(
            self,
            queue: str,
            payload: object,
            headers: Optional[Dict] = None,
            correlation_id: Optional[str] = None,
            reply_to: Optional[str] = None,
            declare_queue: bool = False,
    ) -> None:
        """
        Publish a message to a queue. Producer is created the first time this is called

        NOTE: This creates ONE connection for the producer and reuses it for subsequent publishes
        :param queue: name of the queue to publish to
        :param payload: message payload
        :param headers: message headers
        :param correlation_id: optional correlation ID for RPC pattern
        :param reply_to: optional reply queue for RPC pattern
        :param declare_queue: if True, ensure queue exists before publishing (Default: False)
        :return: None
        """
        if self._producer is None:
            connection = await self._create_connection()
            self._producer = Producer(connection, self._retry_config)
        await self._producer.publish(queue, payload, headers, correlation_id, reply_to, declare_queue)

    async def add_handler(self, queue: str, handler: Callable) -> None:
        """
        Register a consumer handler for a queue
        :param queue: name of the queue
        :param handler: the callback function to handle messages
        """
        if self._consumer_connection is None:
            self._consumer_connection = await self._create_connection()
        consumer = Consumer(self._consumer_connection, self._retry_config)
        self._consumers.append(consumer)
        await consumer.consume(queue, handler)

    @classmethod
    async def loop(cls):
        """
        Block forever to keep the event loop alive
        """
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

class Producer:
    def __init__(self, connection: AbstractConnection, retry_config: Optional[RetryConfig] = None):
        self._connection = connection
        self._retry_config = retry_config if retry_config else RetryConfig()
        self._channel = None

    async def publish(
            self,
            queue: str,
            payload: object,
            headers: Optional[Dict] = None,
            correlation_id: Optional[str] = None,
            reply_to: Optional[str] = None,
            declare_queue: bool = False,
    ) -> None:
        """
        Publish a message to a queue
        :param queue: the name of the queue to publish to
        :param payload: the payload to be published
        :param headers: the message headers
        :param correlation_id: optional correlation ID for RPC pattern
        :param reply_to: optional reply queue for RPC pattern
        :param declare_queue: if True, ensure queue exists before publishing (Default: False)
        :return: None
        """
        assert self._connection is not None
        if self._channel is None:
            self._channel = await self._connection.channel()

        if declare_queue:
            await self._channel.declare_queue(queue, durable=True)

        body = json.dumps(payload).encode('utf-8')
        m = Message(
            body=body,
            headers=headers,
            correlation_id=correlation_id,
            reply_to=reply_to,
            delivery_mode=DeliveryMode.PERSISTENT
        )
        await self._channel.default_exchange.publish(m, routing_key=queue)

    async def close(self):
        """ Close the Producer """
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()

class Consumer:
    def __init__(self, connection: AbstractConnection, retry_config: Optional[RetryConfig] = None):
        self._connection = connection
        self._retry_config = retry_config if retry_config else RetryConfig()
        self._channel = None
        self._retry_exchange = None
        self._dlq_exchange = None
        self._max_retries = len(self._retry_config.retry_delays)

    def is_transient_error(self, exception: Exception) -> bool:
        """
        Determine if an exception is a transient error that should be retried
        :param exception: the exception to check
        :return: True if the error is a transient error, False otherwise
        """
        return isinstance(exception, self._retry_config.retryable_exceptions)

    @classmethod
    def _get_retry_count(cls, msg: AbstractIncomingMessage) -> int:
        """
        Get the current retry count
        :param msg: the message
        :return: the retry count
        """
        if msg.headers and 'x-retry-count' in msg.headers:
            return int(msg.headers['x-retry-count'])
        return 0

    async def _create_retry_queue(self, queue, delay):
        """
        Create a retry queue for the given delay
        :param queue: The name of the main queue
        :param delay: The given delay
        :return: the retry queue
        """
        retry_queue_name = f"{queue}.{delay}"
        retry_queue = await self._channel.declare_queue(
            retry_queue_name,
            durable=True,
            arguments={
                'x-message-ttl': delay, # Message expiration
                'x-dead-letter-exchange': '',  # Default exchange
                'x-dead-letter-routing-key': queue, # Route back to main queue
                'x-expires': delay * 2 # Auto-delete if queue is unused
            }
        )
        await retry_queue.bind(self._retry_exchange, retry_queue_name)
        return retry_queue

    async def _publish_to_retry_queue(
            self,
            queue: str,
            payload: object,
            original_msg: AbstractIncomingMessage,
            retry_count: int
    ) -> None:
        """
        Publish the message to the appropriate retry queue.
        The retry queue has a TTL, after which RabbitMQ will automatically route the message back to the main queue.
        :param queue: name of the main queue
        :param payload: message payload
        :param original_msg: original message
        :param retry_count: current retry count
        :return: None
        """
        if self._retry_exchange is None:
            self._retry_exchange = await self._channel.declare_exchange(
                'retry.exchange',
                ExchangeType.TOPIC,
                durable=True
            )

        delay = self._retry_config.retry_delays[retry_count]
        retry_queue = await self._create_retry_queue(queue, delay)
        headers = dict(original_msg.headers) if original_msg.headers else {}
        headers['x-retry-count'] = retry_count + 1

        body = json.dumps(payload).encode('utf-8')
        m = Message(body=body, headers=headers, delivery_mode=DeliveryMode.PERSISTENT)
        await self._retry_exchange.publish(m, routing_key=retry_queue.name)
        # delay_format = self._retry_config.format_delay(delay)

    async def _send_to_dlq(
            self,
            queue: str,
            payload: object,
            original_msg: AbstractIncomingMessage,
            error: Exception,
            reason: str = ""
    ) -> None:
        """
        Send the message to the appropriate dead letter queue.
        :param queue: name of the main queue
        :param payload: message payload
        :param original_msg: original message
        :param error: the occurred error
        :param reason: why this message was dead lettered
        :return: None
        """
        if self._dlq_exchange is None:
            self._dlq_exchange = await self._channel.declare_exchange(
                'dlq.exchange',
                ExchangeType.TOPIC,
                durable=True
            )
        dlq_name = f"{queue}.dlq"
        headers = dict(original_msg.headers) if original_msg.headers else {}
        headers['x-death-reason'] = reason or str(error)
        headers['x-death-exception-type'] = type(error).__name__

        dlq = await self._channel.declare_queue(dlq_name, durable=True)
        await dlq.bind(self._dlq_exchange, dlq_name)

        body = json.dumps(payload).encode('utf-8')
        m = Message(body=body, headers=headers, delivery_mode=DeliveryMode.PERSISTENT)
        await self._dlq_exchange.publish(m, routing_key=dlq_name)

    async def consume(self, queue: str, handler: Callable) -> None:
        """
        Start consuming from the given queue.
        :param queue: the name of the queue to consume from
        :param handler: the callback function to handle messages
        :return: None
        """
        assert self._connection is not None
        ch = await self._connection.channel()
        self._channel = ch
        await ch.set_qos(prefetch_count=1)
        q = await ch.declare_queue(queue, durable=True)

        async def on_message(msg: AbstractIncomingMessage) -> None:
            try:
                payload = json.loads(msg.body.decode('utf-8'))
            except json.JSONDecodeError:
                payload = msg.body.decode('utf-8')

            retry_count = self._get_retry_count(msg)
            try:
                await handler(payload, msg)
                await msg.ack()
            except Exception as e:
                if self.is_transient_error(e) and retry_count < self._max_retries:
                    await msg.ack()
                    await self._publish_to_retry_queue(queue, payload, msg, retry_count)
                else:
                    await msg.nack(requeue=False)
                    await self._send_to_dlq(queue, payload, msg, e)
        await q.consume(on_message, no_ack=False)