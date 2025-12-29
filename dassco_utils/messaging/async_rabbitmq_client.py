import asyncio
import json
from typing import Callable, Optional, Dict
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractConnection, AbstractIncomingMessage

class ConnectionOptions(object):
    host_name: str = 'localhost'
    username: str = 'guest'
    password: str = 'guest'
    enable_tls: bool = False

class AsyncRabbitMqClient:
    def __init__(self, options: ConnectionOptions = None):
        self._options = options if options else ConnectionOptions()
        self._producer = None
        self._consumer = None

    async def _create_connection(self) -> AbstractConnection:
        url = f"amqp://{self._options.username}:{self._options.password}@{self._options.host_name}/"
        connection = await connect_robust(url)
        return connection

    async def publish(self, queue: str, payload: object, headers: Optional[Dict] = None) -> None:
        if self._producer is None:
            connection = await self._create_connection()
            self._producer = Producer(connection)
        await self._producer.publish(queue, json.dumps(payload), headers)

    async def add_handler(self, queue: str, handler: Callable) -> None:
        if self._consumer is None:
            connection = await self._create_connection()
            self._consumer = Consumer(connection)
        await self._consumer.consume(queue, handler)

    @classmethod
    async def loop(cls):
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

class Producer:
    def __init__(self, connection: AbstractConnection):
        self._connection = connection
        self._channel = None

    async def publish(self, queue_name: str, payload: object, headers: Optional[Dict] = None) -> None:
        assert self._connection is not None
        if self._channel is None:
            self._channel = await self._connection.channel()

        q = await self._channel.declare_queue(queue_name, durable=True)
        body = json.dumps(payload).encode('utf-8')
        m = Message(body=body, headers=headers, delivery_mode=DeliveryMode.PERSISTENT)
        await self._channel.default_exchange.publish(m, routing_key=q.name)

    async def close(self):
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()

class Consumer:
    def __init__(self, connection: AbstractConnection):
        self._connection = connection
        self._consumer_tasks: list[asyncio.Task] = []

    async def consume(self, queue_name: str, handler: Callable) -> None:
        assert self._connection is not None
        ch = await self._connection.channel()
        q = await ch.declare_queue(queue_name, durable=True)

        async def on_message(msg: AbstractIncomingMessage) -> None:
            try:
                payload = json.loads(msg.body.decode('utf-8'))
            except json.JSONDecodeError:
                payload = msg.body.decode('utf-8')
            try:
                await handler(payload, msg)
                await msg.ack()
            except Exception as e:
                print(e)
                await msg.nack(requeue=False)

        await q.consume(on_message, no_ack=False)
