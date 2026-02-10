import asyncio
from dassco_utils.messaging import AsyncRabbitMqClient, RetryConfig
from dassco_utils.messaging.exceptions import TransientError

async def handler_one(msg, props):
    print('Handler One Running')
    raise TransientError('Transient Error')

async def main():
    config = RetryConfig()
    config.retry_delays = [1000, 2000, 5000]
    client = AsyncRabbitMqClient()
    await client.publish('test_queue', 'Hello World')
    await client.add_handler('test_queue', handler_one)
    await client.loop()

asyncio.run(main())