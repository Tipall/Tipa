import asyncio
import curses
import os
import sys
import time
from asyncio import Future
from curses import wrapper
from enum import Enum
from pathlib import Path
from threading import Thread
from typing import cast, Type

from torna.components import BaseOutboundHandler, OutboundClient
from torna.constants import Url

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir.absolute()))

from tipa.console.screen import Screen

WELCOME = """
 ___ ____    _    ____    ____ _           _      ____ _     ___ 
 |_ _/ ___|  / \  / ___|  / ___| |__   __ _| |_   / ___| |   |_ _|
  | |\___ \ / _ \| |     | |   | '_ \ / _` | __| | |   | |    | | 
  | | ___) / ___ \ |___  | |___| | | | (_| | |_  | |___| |___ | | 
 |___|____/_/   \_\____|  \____|_| |_|\__,_|\__|  \____|_____|___|                                                           
"""


class IsacHandler(BaseOutboundHandler):
    def __init__(self, url: str, cli, **kwargs):
        super().__init__(url, **kwargs)
        self.cli = cli

    async def on_open(self):
        self.cli.connect_waiter.set_result(True)


def OutboundClient(url: Url, handler: Type[BaseOutboundHandler],
                   loop: asyncio.AbstractEventLoop = None,
                   **kwargs,
                   ) -> BaseOutboundHandler:
    new_cls = handler.generate_event_handler()
    new_cls = cast(Type[BaseOutboundHandler], new_cls)
    return new_cls(url, loop=loop, **kwargs)


class ChatCLIMode(int, Enum):
    Command = 1
    Interactive = 2
    FreeTalk = 3
    AutoTalk = 4
    ManualTalk = 4


class IsacChatCLI:
    def __init__(self):
        super().__init__()
        self.done = False
        self.scr = None
        self.client = None
        self.connect_waiter = None
        self._loop = asyncio.get_event_loop()
        self.mode = ChatCLIMode.Command
        self._commands = {
            "q": self.quit,
        }
        self.width, self.height = os.get_terminal_size()

    def run(self):
        curses.wrapper(self._main)

    def _main(self, scr):
        self.scr = scr
        curses.noecho()
        curses.cbreak()
        self.scr.keypad(True)
        self.scr.clear()

        try:
            self.on_start()
            while not self.done:
                self.on_loop()
        except (KeyboardInterrupt, Exception):
            pass
        finally:
            self.on_end()

        curses.endwin()

    def on_start(self):
        self.scr.addstr(WELCOME)
        self.scr.addstr("\n")
        self.scr.refresh()

        self.loop_thread = Thread(self.connect())
        self.loop_thread.start()

        self.scr.addstr(f"w:{self.width} h:{self.height}\n")
        self.scr.addstr(self.height - 1, 0, "Q Quit\tR Reset")
        self.scr.refresh()

        # self._listen_key_task = self._loop.create_task(self.on_press())

    def connect(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.connect_async())

    async def connect_async(self):
        self.client = OutboundClient(
            "ws://localhost:8397/ws",
            IsacHandler,
            cli=self,
        )
        loop = asyncio.get_event_loop()
        loop.create_task(
            self.client.connect()
        )

        self.connect_waiter = Future()
        await self.connect_waiter

        self.scr.addstr("[*] Client connected.\n")
        self.scr.refresh()

    def on_loop(self):
        key = self.scr.getkey()
        cmd = self._commands.get(key)
        if cmd:
            cmd()

    def on_end(self):
        pass

    def quit(self):
        self.done = True

    def reset(self):
        pass

    # def add_line(self, text):
    #     self.scr.addstr(self._line_count, text)
    #     self.scr.add_str(self.height, self.help_text)
    #     self._line_count += 1
    #     self.scr.refresh()


if __name__ == '__main__':
    IsacChatCLI().run()
