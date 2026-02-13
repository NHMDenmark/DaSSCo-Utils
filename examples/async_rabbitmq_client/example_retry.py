import asyncio
from dassco_utils.messaging import AsyncRabbitMqClient, RetryConfig
from dassco_utils.messaging.exceptions import TransientError

async def handler_one(msg, props):
    print('Handler One Running')
    # Sync med Erda
    raise TransientError('Transient Error')

async def main():
    config = RetryConfig()
    config.retry_delays = [1000, 1000, 1000]
    client = AsyncRabbitMqClient(retry_config=config)
    await client.publish('test_queue', 'Hello World')
    await client.add_handler('test_queue', handler_one)
    await client.loop()

asyncio.run(main())