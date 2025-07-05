import asyncio
import inspect
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Any, Coroutine
from aiogram.exceptions import TelegramForbiddenError
from contextlib import asynccontextmanager
from app.util.logger import logger

MINIMAL_SAFE_SECONDS_DELAY = 60

class TimerManager:
    def __init__(self, func: Callable[[str, "TimerManager"], Any], delay: float | int | datetime | Callable[[str, int], float | int | datetime | None | Coroutine[Any, Any, float | int | datetime | None]] | None, name = 'timer'):
        self.tasks: dict[str, asyncio.Task] = {}
        self.name = name
        self.func = func
        self.delay = delay
    

    async def _get_delay(self, key: str, count: int):
        result = None
        now = datetime.now(timezone.utc)
        try:
            if isinstance(self.delay, float | int | datetime):
                result = self.delay
            elif inspect.iscoroutinefunction(self.delay):
                result = await self.delay(key, count)
            elif inspect.isfunction(self.delay):
                result = self.delay(key, count)
            else:
                raise ValueError(f'Unexpected delay parameter type: {type(self.delay)}')
            
            if isinstance(result, float | int):
                result = max(result, MINIMAL_SAFE_SECONDS_DELAY)
            elif isinstance(result, datetime):
                result = max((result - now).total_seconds(), MINIMAL_SAFE_SECONDS_DELAY)
            elif result is None:
                return None
            else:
                raise ValueError(f'Unexpected delay result type: {type(result)}')
        except Exception as e:
            logger.error(f'{self.name.capitalize()} task manager says: Problem with getting delay to process [{key}]:\n{e}')
        finally:
            if isinstance(result, float | int):
                deadline = now + timedelta(seconds=result)
                days_diff = (deadline.date() - now.date()).days
                deadline_str = deadline.strftime('%H:%M:%S') + (f' (+{days_diff})' if days_diff else '') + ' utc'
                logger.debug(f'{self.name.capitalize()} task [{key}] scheduled to {deadline_str} ({int(result)}s)')
                return result
            else:
                return None
    
    
    async def _call_func(self, key: str):
        try:
            if inspect.iscoroutinefunction(self.func):
                await self.func(key, self)
            else:
                self.func(key, self)
        except Exception as e:
            logger.error(f'{self.name.capitalize()} task manager says: Problem with delayed processing of [{key}]: {e}')
    

    async def _delayed_call(self, key: str):
        async with cancellable(self, key):
            delay = await self._get_delay(key, 1)
            if delay:
                await asyncio.sleep(delay)
                await self._call_func(key)
    

    async def _repeated_call(self, key: str, repeat: Optional[int] = None):
        async with cancellable(self, key):
            count = 0
            while repeat is None or count < repeat:
                delay = await self._get_delay(key, count + 1)
                if delay:
                    await asyncio.sleep(delay)
                    await self._call_func(key)
                    count += 1
                else:
                    break


    def _store_task(self, key: str, task: asyncio.Task):
        self.tasks[key] = task

    async def _cancel_existing(self, key: str):
        task = self.tasks.get(key)
        # logger.debug(f'Cancelling {self.name} task [{key}] {f'exists and {'done' if task.done() else 'not done'}' if task else 'not found'}')
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self.tasks.pop(key, None)


    async def once_one(self, key: str):
        # logger.debug(f'Keys before canceling: {", ".join(self.tasks.keys())}')
        await self._cancel_existing(key)
        # logger.debug(f'Keys after canceling: {", ".join(self.tasks.keys())}')
        task = asyncio.create_task(self._delayed_call(key))
        self._store_task(key, task)
        return task

    async def once_all(self, keys: Optional[list[str]] = None):
        all_keys = set(self.tasks.keys()).union(keys or [])
        for key in all_keys:
            await self.once_one(key)

    
    async def loop_one(self, key: str, times: Optional[int] = None):
        await self._cancel_existing(key)
        task = asyncio.create_task(self._repeated_call(key, times))
        self._store_task(key, task)

    async def loop_all(self, keys: Optional[list[str]] = None, times: Optional[int] = None):
        all_keys = set(self.tasks.keys()).union(keys or [])
        for key in all_keys:
            await self.loop_one(key, times)


    async def stop_one(self, key: str):
        await self._cancel_existing(key)
        self.tasks.pop(key, None)

    async def stop_all(self):
        task_keys = list(self.tasks.keys())
        for key in task_keys:
            await self._cancel_existing(key)
            self.tasks.pop(key, None)


    def keys(self):
        return list(self.tasks.keys())



@asynccontextmanager
async def cancellable(manager: TimerManager, key: str):
    try:
        yield
    except asyncio.CancelledError:
        logger.debug(f'{manager.name.capitalize()} task [{key}] cancelled')
        raise
    except TelegramForbiddenError:
        pass
    except Exception as e:
        logger.error(f'Error in {manager.name} task manager: {e}')
    # finally:
        # manager.tasks.pop(key, None)

