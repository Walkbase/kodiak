"""
based on https://github.com/kiwicom/structlog-sentry/blob/18adbfdac85930ca5578e7ef95c1f2dc169c2f2f/structlog_sentry/__init__.py#L10-L86
MIT License

Copyright (c) 2019 Kiwi.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from sentry_sdk import capture_event
from sentry_sdk.utils import event_from_exception
from typing_extensions import Literal

EventDict = Dict[str, Any]
SentryLevel = Literal["fatal", "error", "warning", "info", "debug"]
SentryTagKeys = Optional[Union[List[str], Literal["__all__"]]]


def get_logging_level(name: str) -> int:
    return logging._nameToLevel[name.upper()]


def _get_event_and_hint(
    *, event_dict: EventDict, level: SentryLevel, tag_keys: SentryTagKeys
) -> Tuple[EventDict, EventDict]:
    original_event_dict = event_dict.copy()

    exc_info = event_dict.pop("exc_info", sys.exc_info())
    has_exc_info = exc_info and exc_info != (None, None, None)

    if has_exc_info:
        event, hint = event_from_exception(exc_info)
    else:
        event = {}
        hint = {}

    event["message"] = event_dict.get("event")
    event["level"] = level
    event["extra"] = original_event_dict

    if tag_keys == "__all__":
        event["tags"] = original_event_dict
    elif isinstance(tag_keys, list):
        event["tags"] = {key: event_dict[key] for key in tag_keys if key in event_dict}

    return event, hint


def send_event_to_sentry(
    *, event_dict: EventDict, level: SentryLevel, tag_keys: SentryTagKeys
) -> Optional[str]:
    event, hint = _get_event_and_hint(
        event_dict=event_dict, level=level, tag_keys=tag_keys
    )
    return capture_event(event, hint=hint)


class SentryProcessor:
    """
    Sentry processor for structlog.
    """

    def __init__(
        self, level: int = logging.WARNING, tag_keys: SentryTagKeys = None
    ) -> None:
        self.level = level
        self.tag_keys = tag_keys

    def __call__(
        self, logger: Any, level: SentryLevel, event_dict: EventDict
    ) -> EventDict:
        if get_logging_level(level) < self.level:
            return event_dict

        event_dict["sentry_id"] = send_event_to_sentry(
            event_dict=event_dict, level=level, tag_keys=self.tag_keys
        )

        return event_dict
