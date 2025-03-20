#! /usr/bin/env python

import datetime
import io
import json
import os
from pathlib import Path

from PIL import Image
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
# from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (Footer, Header, Label, ListItem, ListView,
                             LoadingIndicator, Select, Static)
from textual_image.widget import Image as ImageWidget

from slacktui.config import load_config
from slacktui.database import load_channels, load_file, load_messages
from slacktui.files import get_file_data
from slacktui.text import format_text_item


class ImageViewScreen(ModalScreen):

    BINDINGS = [
        ("escape", "quit", "Close image viewer"),
        ("left", "prev_image", "Previous image"),
        ("right", "next_image", "Next image"),
        ("r", "refresh", "Refresh"),
    ]
    files = None
    file_index = reactive(0, repaint=False)

    def __init__(self, *args, files=None, **kwds):
        super().__init__(*args, **kwds)
        self.files = files

    def make_image_widget(self, image_data):
        buf = io.BytesIO(image_data)
        pil_image = Image.open(buf)
        w, h = pil_image.size
        if w >= h:
            style_class = "image-widget-wide"
        else:
            style_class = "image-wideget-tall"
        return ImageWidget(pil_image, classes=f"image-widget {style_class}")

    def compose(self):
        yield LoadingIndicator(classes="image-widget")

    def get_image_data(self, file_id):
        file_info = load_file(self.app.workspace, file_id)
        if file_info is None:
            self.app.get_file_from_slack(file_id, callback=self.process_file)
        else:
            self.process_file(file_info)

    def process_file(self, file_info):
        self.query(".image-widget").remove()
        self.query(".image-caption").remove()
        file_data = file_info["data"]
        image_widget = self.make_image_widget(file_data)
        title = file_info["title"]
        caption = Label(title, classes="image-caption")
        self.mount(image_widget)
        self.mount(caption)

    def action_quit(self):
        self.app.pop_screen()

    def action_prev_image(self):
        self.file_index = max(0, self.file_index - 1)

    def action_next_image(self):
        size = len(self.files)
        self.file_index = min(size - 1, self.file_index + 1)

    def action_refresh(self):
        self.query(".image-widget").refresh()

    def watch_file_index(self, new_index):
        file_id = self.files[self.file_index]["id"]
        self.get_image_data(file_id)


class MessageListItem(ListItem):

    files = None

    def __init__(self, *args, files=None, **kwds):
        super().__init__(*args, **kwds)
        self.files = files


class SlackApp(App):
    """
    Slack viewer app.
    """

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("i", "view_images", "View images"),
    ]
    image_types = frozenset(["image/jpeg", "image/png", "image/gif"])
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

    def action_view_images(self):
        listview = self.query_one("#messages")
        if listview.index is not None:
            listitem = listview.children[listview.index]
            if listitem.files is None or len(listitem.files) == 0:
                return
            screen = ImageViewScreen(files=listitem.files)
            self.push_screen(screen)

    @on(Select.Changed)
    def handle_select(self, event):
        listview = self.query_one("#messages")
        listview.clear()
        messages = load_messages(self.workspace, event.value)
        list_items = []
        for message_info in messages:
            ts = message_info["ts"]
            user = message_info["user"]
            files_json = message_info["files_json"]
            message = json.loads(message_info["json_blob"])
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
            text = format_text_item(self.workspace, message)
            # print(json.dumps(message, indent=4))
            # print(text)
            message_text = Static(text, classes="message-text", markup=True)
            rows.append(message_text)
            # file_buttons = []
            file_labels = []
            files = None
            if files_json is not None:
                files = json.loads(files_json)
                for file_info in files:
                    file_label = Label(
                        f"\\[{file_info['title']}]", classes="file-label"
                    )
                    file_labels.append(file_label)
                file_row = Horizontal(*file_labels, classes="file-labels")
                rows.append(file_row)
            list_item = MessageListItem(
                Vertical(
                    *rows,
                    classes="message",
                ),
                files=files,
            )
            list_items.append(list_item)
        listview.extend(list_items)
        if len(list_items) > 0:
            listview.index = 0

    @work(group="file-download", exclusive=True, thread=True)
    def get_file_from_slack(self, file_id, callback=None):
        file_info = get_file_data(self.config, self.workspace, file_id)
        if file_info is None:
            print(f"Could not retrieve file info for ID: {file_id}.")
            return
        print("Retrieved file data.")
        if callback is not None:
            self.call_from_thread(callback, file_info)

    def process_file(self, file_info):
        mimetype = file_info["mimetype"]
        if mimetype in self.image_types:
            file_data = file_info["data"]
            screen = ImageViewScreen()
            screen.image_data = file_data
            self.push_screen(screen)

    @work(thread=True)
    def handle_dl_button_pressed(self, button):
        file_id = button.file_id
        print(f"Pressed download button with file ID: {file_id}")
        file_info = get_file_data(self.config, self.workspace, file_id)
        if file_info is None:
            print(f"Could not retrieve file info for ID {file_id}.")
            return
        print("Retrieved file data.")
        file_data = file_info["data"]
        dl_folder = self.config.get("files", {}).get("download_folder", "~/Downloads")
        dl_folder = Path(dl_folder).expanduser()
        if not dl_folder.is_dir():
            print(f"Path {dl_folder} does not exist or is not a folder.")
            return
        filename = Path(button.filename)
        fname = dl_folder / filename
        n = 0
        while fname.exists():
            n += 1
            if n == 1000:
                print(
                    "Could not generate a unique name for "
                    f"file '{button.filename}' in folder '{dl_folder}'."
                )
                return
            fname = dl_folder / Path(f"{filename.stem}.{n:03}{filename.suffix}")
        with open(fname, "wb") as f:
            f.write(file_data)
        print(f"File written to '{fname}'.")


if __name__ == "__main__":
    app = SlackApp()
    config = load_config(app.workspace)
    app.config = config
    app.run()
