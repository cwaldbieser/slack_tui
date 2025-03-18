#! /usr/bin/env python

import datetime
import json
import os

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (Button, Footer, Header, Label, ListItem, ListView,
                             Select)

from slacktui.database import load_channels, load_messages


class FileButton(Button):

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)


class SlackApp(App):
    """
    Slack viewer app.
    """

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    workspace = os.environ["SLACK_WORKSPACE"]

    def compose(self) -> ComposeResult:
        """
        Create child widgets for the app.
        """
        channel_map = {}
        for id, name in load_channels(self.workspace):
            channel_map[name] = id
        self.channel_map = channel_map

        yield Header()
        with Vertical():
            yield Select.from_values(channel_map.keys())
            yield ListView(id="messages")
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    @on(Select.Changed)
    def handle_select(self, event):
        listview = self.query_one("#messages")
        listview.clear()
        listview.can_focus_children = True
        print("Cleared listview.")
        messages = load_messages(self.workspace, event.value)
        list_items = []
        for ts, user, text, files_json in messages:
            formatted_time = datetime.datetime.fromtimestamp(float(ts)).strftime(
                "%I:%M %p"
            )
            rows = []
            user_ts = Horizontal(
                Label(user, classes="user"),
                Label(formatted_time, classes="timestamp"),
                classes="user-ts",
            )
            rows.append(user_ts)
            message_text = Label(text, classes="message-text")
            rows.append(message_text)
            file_buttons = []
            if files_json is not None:
                files = json.loads(files_json)
                for file_info in files:
                    button = FileButton(
                        file_info["title"], classes="file-button", variant="primary"
                    )
                    file_buttons.append(button)
                file_row = Horizontal(*file_buttons, classes="file-buttons")
                rows.append(file_row)
            list_item = ListItem(
                Vertical(
                    *rows,
                    classes="message",
                )
            )
            list_items.append(list_item)
        listview.extend(list_items)
        if len(list_items) > 0:
            listview.index = 0


if __name__ == "__main__":
    app = SlackApp()
    app.run()
