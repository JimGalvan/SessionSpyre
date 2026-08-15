import asyncio
import sys

if sys.platform == "win32":
    # pytest-django loads Django settings, which pulls in channels/daphne and
    # installs a Twisted asyncio reactor. That reactor forces the Selector
    # event loop policy on Windows, but Playwright's driver needs Proactor to
    # spawn its Node.js subprocess — without this it fails with
    # "NotImplementedError" from asyncio.base_events._make_subprocess_transport.
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
