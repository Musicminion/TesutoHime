__import__('judger2.logging_')

from asyncio import CancelledError, create_task, run, sleep, wait
from atexit import register
from logging import getLogger
from time import time

from commons.task_typing import (StatusUpdateDone, StatusUpdateError,
                                 StatusUpdateStarted)
from commons.util import deserialize, format_exc, serialize

from judger2.cache import clean_cache_worker
from judger2.config import (heartbeat_interval_secs, poll_timeout_secs, queues,
                            redis_connect, runner_id, task_timeout_secs)
from judger2.logging_ import task_logger
from judger2.task import run_task

logger = getLogger(__name__)


async def send_heartbeats():
    redis = redis_connect()
    while True:
        try:
            await redis.set(queues.heartbeat, time())
        except CancelledError:
            return
        except BaseException as e:
            logger.error(f'error sending heartbeat: {e}')
        await sleep(heartbeat_interval_secs)


async def poll_for_tasks():
    redis = redis_connect()
    await redis.delete(queues.in_progress)
    while True:
        task_id = None
        try:
            task_id = await redis.brpoplpush(
                queues.tasks,
                queues.in_progress,
                poll_timeout_secs,
            )
            if task_id is None: continue
            task_queues = queues.task(task_id)
            async def report_progress(status):
                await redis.lpush(task_queues.progress, serialize(status))
                await redis.expire(task_queues.progress, task_timeout_secs)

            task = deserialize(await redis.lpop(task_queues.task))
            aio_task = create_task(run_task(task, task_id))
            await report_progress(StatusUpdateStarted())

            async def poll_for_abort_signal():
                redis = redis_connect()
                while True:
                    try:
                        message = await redis.blpop(task_queues.abort,
                            poll_timeout_secs)
                        if message == None: continue
                        aio_task.cancel()
                        return
                    except Exception as e:
                        logger.error(f'Error processing signal: {e}')
                        await sleep(2)
            abort_task = create_task(poll_for_abort_signal())

            try:
                result = await aio_task
                abort_task.cancel()
                task_logger.debug(f'task {task_id} completed with {result}')
                await report_progress(StatusUpdateDone(result))
            except CancelledError:
                task_logger.info(f'task {task_id} was aborted')
            normal_completion = True
        except CancelledError:
            normal_completion = False
            error = 'Aborted'
            return
        except BaseException as e:
            normal_completion = False
            error = ''.join(format_exc(e))
            task_logger.error(f'error processing task: {error}')
            await sleep(2)
        finally:
            if task_id is not None:
                try:
                    await redis.lrem(queues.in_progress, 0, task_id)
                except BaseException as e:
                    task_logger.error(f'error removing task from queue: {e}')
                if not normal_completion:
                    try:
                        await report_progress(StatusUpdateError(error))
                    except BaseException as e:
                        task_logger.error(f'error sending nack: {e}')


async def main():
    logger.info(f'runner {runner_id} starting')
    register(lambda: logger.info(f'runner {runner_id} stopping'))
    await wait([
        create_task(send_heartbeats()),
        create_task(poll_for_tasks()),
        create_task(clean_cache_worker()),
    ])

if __name__ == '__main__':
    try:
        run(main())
    except KeyboardInterrupt:
        pass
