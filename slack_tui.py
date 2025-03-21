#! /usr/bin/env python

import datetime
import io
import json
import os
from hashlib import md5
from pathlib import Path

import emoji
from PIL import Image
from rich.emoji import Emoji
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
# from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (Checkbox, Footer, Header, Label, ListItem,
                             ListView, LoadingIndicator, Select, Static,
                             TextArea)
from textual_image.widget import Image as ImageWidget

from slacktui.config import load_config
from slacktui.database import (load_channels, load_file, load_messages,
                               load_users, store_message)
from slacktui.files import get_file_data
from slacktui.messages import get_history_for_channel, post_message
from slacktui.text import format_text_item

_REACTION_ALIASES = {
    "+1": "thumbs_up",
}


def get_emoji_from_code(code):
    global _REACTION_ALIASES
    if len(code) == 0:
        return code
    if code[0] != ":":
        code = f":{code}"
    if code[-1] != ":":
        code = f"{code}:"
    symbol = Emoji.replace(code)
    if symbol != code:
        return symbol
    symbol = emoji.emojize(code)
    if symbol != code:
        return symbol
    return _REACTION_ALIASES.get(code, code)


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


def compute_message_digest(json_blob):
    cannonical = json.dumps(json.loads(json_blob), sort_keys=True)
    hash = md5(cannonical.encode())
    digest = hash.hexdigest()
    return digest


class MessageListItem(ListItem):

    files = None
    reactions = None
    digest = None

    def __init__(self, *args, files=None, reactions=None, message=None, **kwds):
        super().__init__(*args, **kwds)
        self.files = files
        self.reactions = reactions
        cannonical = json.dumps(message, sort_keys=True)
        hash = md5(cannonical.encode())
        digest = hash.hexdigest()
        self.digest = digest


def ts2id(ts):
    widget_id = f"msg-{ts.replace(".", "-")}"
    return widget_id


def id2ts(widget_id):
    ts = widget_id[4:].replace("-", ".")
    return ts


class SlackApp(App):
    """
    Slack viewer app.
    """

    CSS_PATH = "app.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("i", "view_images", "View images"),
        ("shift+enter", "send_message", "Send message"),
        ("shift+down", "scroll_bottom", "Scroll to bottom"),
    ]
    image_types = frozenset(["image/jpeg", "image/png", "image/gif"])
    history_sync_days = 7
    refresh_timer = None
    workspace = os.environ["SLACK_WORKSPACE"]
    config = None
    channel_map = None
    channel_id = None

    def compose(self) -> ComposeResult:
        """
        Create child widgets for the app.
        """
        channel_map = {}
        for id, name, user_id in load_channels(self.workspace):
            channel_map[name] = id
        self.channel_map = channel_map
        user_map = {}
        for user_info in load_users(self.workspace):
            user_id = user_info["id"]
            username = user_info["name"]
            display_name = user_info["display_name"]
            user_map[user_id] = (username, display_name)
        self.user_map = user_map
        yield Header()
        with Vertical():
            with Horizontal():
                yield Checkbox("DMs", id="dm-checkbox", classes="dm-toggle")
                yield Select.from_values(channel_map.keys(), id="channel-select")
            yield ListView(id="messages")
            yield TextArea(id="composer")
        yield Footer()

    def on_mount(self):
        self.refresh_timer = self.set_interval(
            3, self.refresh_messages, name="sync-interval", pause=True
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_scroll_bottom(self):
        listview = self.query_one("#messages")
        children = listview.children
        if len(children) == 0:
            return
        child = children[-1]
        listview.scroll_to_widget(child)
        listview.index = len(children) - 1

    def action_view_images(self):
        listview = self.query_one("#messages")
        if listview.index is not None:
            listitem = listview.children[listview.index]
            if listitem.files is None or len(listitem.files) == 0:
                return
            screen = ImageViewScreen(files=listitem.files)
            self.push_screen(screen)

    def action_send_message(self):
        if self.channel_id is None:
            return
        textarea = self.query_one("#composer")
        text = textarea.text
        print(f"Sending message to channel ID {self.channel_id}: {text}")
        post_message(self.config, self.channel_id, text)
        textarea.clear()

    @on(Checkbox.Changed)
    def handle_dm_toggle(self, event):
        channel_select = self.query_one("#channel-select")
        channel_map = {}
        is_dm = event.checkbox.value
        for id, name, user_id in load_channels(self.workspace, load_dms=is_dm):
            if is_dm:
                username, display_name = self.user_map[user_id]
                name = display_name
            channel_map[name] = id
        print(f"channel_map: {channel_map}")
        self.channel_map = channel_map
        options = [(key, key) for key in channel_map.keys()]
        channel_select.set_options(options)

    @on(Select.Changed)
    async def handle_select(self, event):
        self.refresh_timer.pause()
        listview = self.query_one("#messages")
        await listview.clear()
        if event.value == Select.BLANK:
            self.channel_id = None
            return
        self.channel_id = self.channel_map[event.value]
        messages = load_messages(self.workspace, self.channel_id)
        list_items = []
        for message_info in messages:
            list_item = self.create_message_list_item(message_info)
            list_items.append(list_item)
        await listview.extend(list_items)
        self.set_timer(0.5, self.action_scroll_bottom())
        self.sync_channel_history()

    @work(group="refresh-messages", exclusive=True, thread=True)
    def refresh_messages(self):
        try:
            channel_select = self.query_one("#channel-select")
        except NoMatches:
            return
        channel = channel_select.value
        if channel == Select.BLANK:
            return
        messages = list(load_messages(self.workspace, self.channel_id))
        self.call_from_thread(self.refresh_messages_ui, messages)

    async def refresh_messages_ui(self, messages):
        listview = self.query_one("#messages")
        orig_index = listview.index
        list_items = list(listview.children)
        if orig_index is None or orig_index == len(list_items) - 1:
            self.app.set_timer(0.5, self.action_scroll_bottom)
        if len(list_items) == 0:
            # add all messages
            print("No list items.  Adding all messages from DB.")
            list_items = []
            for message in messages:
                list_item = self.create_message_list_item(message)
                await listview.append(list_item)
            self.action_scroll_bottom()
            return
        if len(messages) == 0:
            print("No messages in DB.  Clearing list items.")
            await listview.clear()
            return
        list_item_id_map = dict(
            (id2ts(li.id), (n, li.digest)) for n, li in enumerate(list_items)
        )
        list_item_ids = set(list_item_id_map.keys())
        dbmsg_id_map = dict((m["ts"], m) for m in messages)
        dbmsg_ids = set(dbmsg_id_map.keys())
        # Remove items not in DB
        not_in_db = list_item_ids - dbmsg_ids
        indicies_to_remove = []
        for index, list_item in enumerate(list_items):
            ts = id2ts(list_item.id)
            if ts in not_in_db:
                await indicies_to_remove.append(index)
        listview.remove_items(indicies_to_remove)
        # Add messages not in list view
        not_in_lv = dbmsg_ids - list_item_ids
        for message in messages:
            ts = message["ts"]
            if ts in not_in_lv:
                msg_list_item = self.create_message_list_item(message)
                await listview.append(msg_list_item)
        # Determine if any messages already in the list view changed.
        same_ids = list_item_ids & dbmsg_ids
        for shared_id in same_ids:
            # Compute digest of DB message
            message = dbmsg_id_map[shared_id]
            computed_digest = compute_message_digest(message["json_blob"])
            # Compare to digest of list item message
            pos, stored_digest = list_item_id_map[shared_id]
            if computed_digest != stored_digest:
                # Insert new message and remove old message
                msg_list_item = self.create_message_list_item(message)
                await listview.pop(pos)
                await listview.insert(pos, [msg_list_item])

    def create_message_list_item(self, message_info):
        ts = message_info["ts"]
        user = message_info["user"]
        files_json = message_info["files_json"]
        message = json.loads(message_info["json_blob"])
        formatted_time = datetime.datetime.fromtimestamp(float(ts)).strftime(
            "%Y-%m-%d %I:%M %p"
        )
        rows = []
        status_components = [
            Label(user, classes="user"),
            Label(formatted_time, classes="timestamp"),
        ]
        reactions = message.get("reactions")
        if reactions is not None:
            symbols = []
            for reaction in reactions:
                react_name = reaction["name"]
                react_count = reaction["count"]
                emoji_symbol = get_emoji_from_code(react_name)
                symbols.append(f"{emoji_symbol}x{react_count}")
            react_str = " ".join(symbols)
            status_components.append(Static(react_str, classes="reactions"))
        msg_status_bar = Horizontal(
            *status_components,
            classes="msg-status-bar",
        )
        rows.append(msg_status_bar)
        text = format_text_item(self.workspace, message)
        # print(json.dumps(message, indent=4))
        # print(text)
        message_text = Static(text, classes="message-text", markup=True)
        rows.append(message_text)
        file_labels = []
        files = None
        if files_json is not None:
            files = json.loads(files_json)
            for file_info in files:
                file_label = Label(f"\\[{file_info['title']}]", classes="file-label")
                file_labels.append(file_label)
            file_row = Horizontal(*file_labels, classes="file-labels")
            rows.append(file_row)
        list_item = MessageListItem(
            Vertical(
                *rows,
                classes="message",
            ),
            files=files,
            reactions=reactions,
            id=ts2id(ts),
            message=message,
        )
        return list_item

    @work(group="sync-channel", thread=True)
    def sync_channel_history(self):
        history = get_history_for_channel(
            self.config, self.channel_id, self.history_sync_days
        )
        for message in history:
            message["channel"] = self.channel_id
            store_message(self.workspace, message)
        print(
            f"Database synced for {self.history_sync_days} days worth of messages "
            f"for channel ID {self.channel_id}."
        )
        self.refresh_timer.resume()

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
