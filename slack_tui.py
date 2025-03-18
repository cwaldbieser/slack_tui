#! /usr/bin/env python

import datetime
import json
import os

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (Button, Footer, Header, Label, ListItem, ListView,
                             Select)

from slacktui.config import load_config
from slacktui.database import load_channels, load_messages
from slacktui.files import get_file_data


class FileButton(Button):

    file_id = None

    def __init__(self, *args, file_id=None, **kwds):
        super().__init__(*args, **kwds)
        self.file_id = file_id


class SlackApp(App):
    """
    Slack viewer app.
    """

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    workspace = os.environ["SLACK_WORKSPACE"]
    config = None

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
                        file_info["title"],
                        classes="file-button",
                        variant="primary",
                        file_id=file_info["id"],
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

    @on(FileButton.Pressed)
    def handle_file_button_pressed(self, event):
        button = event.button
        file_id = button.file_id
        print(f"Pressed button with file ID: {file_id}")
        get_file_data(self.config, self.workspace, file_id)
        print("Retrieved file data.")


if __name__ == "__main__":
    app = SlackApp()
    config = load_config(app.workspace)
    app.config = config
    app.run()
