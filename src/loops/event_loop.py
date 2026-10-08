"""Loop 3: Event-Driven Loop - Async event processing and orchestration."""
import asyncio
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime
import structlog

from src.models.review import Review

logger = structlog.get_logger()


class EventType(str, Enum):
    """Types of events in the system."""
    NEW_REVIEW = "new_review"
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_PASSED = "verification_passed"
    HILL_CLIMBING_READY = "hill_climbing_ready"
    IMPROVEMENT_AVAILABLE = "improvement_available"
    BATCH_COMPLETE = "batch_complete"


class Event:
    """Event object."""

    def __init__(self, event_type: EventType, data: Any, timestamp: Optional[datetime] = None):
        """Initialize event."""
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"Event({self.event_type}, timestamp={self.timestamp})"


class EventLoop:
    """
    Loop 3: Event-Driven Loop.

    Provides async event processing with:
    - Event queue management
    - Event handlers registration
    - Background task scheduling
    - Rate limiting and backpressure
    """

    def __init__(self):
        """Initialize event loop."""
        self.event_queue = asyncio.Queue()
        self.handlers = {}
        self.running = False
        self.tasks = []

        logger.info("Event Loop initialized")

    def register_handler(self, event_type: EventType, handler: Callable):
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)

        logger.debug(
            "Handler registered",
            event_type=event_type.value,
            handler=handler.__name__
        )

    async def emit(self, event_type: EventType, data: Any):
        """
        Emit an event to the queue.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = Event(event_type, data)
        await self.event_queue.put(event)

        logger.debug(
            "Event emitted",
            event_type=event_type.value,
            queue_size=self.event_queue.qsize()
        )

    async def process_event(self, event: Event):
        """
        Process a single event.

        Args:
            event: Event to process
        """
        handlers = self.handlers.get(event.event_type, [])

        if not handlers:
            logger.warning(
                "No handlers for event",
                event_type=event.event_type.value
            )
            return

        logger.debug(
            "Processing event",
            event_type=event.event_type.value,
            num_handlers=len(handlers)
        )

        # Execute all handlers for this event
        for handler in handlers:
            try:
                await handler(event.data)
            except Exception as e:
                logger.error(
                    "Handler failed",
                    event_type=event.event_type.value,
                    handler=handler.__name__,
                    error=str(e)
                )

    async def run(self):
        """
        Run the event loop (process events from queue).

        This is a long-running task that should be run in the background.
        """
        self.running = True

        logger.info("Event Loop started")

        while self.running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )

                await self.process_event(event)

            except asyncio.TimeoutError:
                # No events, continue
                continue
            except Exception as e:
                logger.error("Event loop error", error=str(e))

        logger.info("Event Loop stopped")

    def stop(self):
        """Stop the event loop."""
        self.running = False
        logger.info("Event Loop stop requested")

    async def schedule_task(
        self,
        task_func: Callable,
        delay: float = 0,
        interval: Optional[float] = None
    ):
        """
        Schedule a background task.

        Args:
            task_func: Async function to run
            delay: Initial delay in seconds
            interval: If set, repeat task at this interval
        """
        async def _run_task():
            if delay > 0:
                await asyncio.sleep(delay)

            while True:
                try:
                    await task_func()
                except Exception as e:
                    logger.error(
                        "Scheduled task failed",
                        task=task_func.__name__,
                        error=str(e)
                    )

                if interval is None:
                    break

                await asyncio.sleep(interval)

        task = asyncio.create_task(_run_task())
        self.tasks.append(task)

        logger.info(
            "Task scheduled",
            task=task_func.__name__,
            delay=delay,
            interval=interval
        )

        return task

    def get_status(self) -> dict:
        """Get event loop status."""
        return {
            "running": self.running,
            "queue_size": self.event_queue.qsize(),
            "num_handlers": sum(len(handlers) for handlers in self.handlers.values()),
            "active_tasks": len([t for t in self.tasks if not t.done()])
        }


# Global event loop instance
event_loop = EventLoop()
