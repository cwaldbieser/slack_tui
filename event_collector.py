#! /usr/bin/env python

import argparse
import json

import logzero
from logzero import logger
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slacktui.channel import query_channels
from slacktui.config import load_config
from slacktui.database import (add_reaction, init_db, mark_channel_unread,
                               remove_reaction, store_channels, store_message,
                               store_users)
from slacktui.user import query_users

app = None
ws = None


def init(args):
    """
    Initialize application.
    """
    logger.info("Loading application configuration.")
    config = load_config(args.workspace)
    log_level = config.get("logging", {"severity": "INFO"}).get("severity", "INFO")
    if log_level in ("ERROR", "WARN", "INFO", "DEBUG"):
        severity = getattr(logzero, log_level)
    else:
        severity = "INFO"
    logzero.loglevel(severity)
    init_app(config)


def init_app(config):
    """
    Initialize app.
    """
    global app
    # Initializes your app with your bot token and socket mode handler
    logger.info("Initializing/authorizing application.")
    user_token = config["oauth"]["user_token"]
    app = App(token=user_token)


def main(args):
    global app
    global ws
    config = load_config(args.workspace)
    init_db(args.workspace)
    channels = query_channels(config)
    store_channels(args.workspace, channels)
    users = query_users(config)
    store_users(args.workspace, users)
    app_token = config["oauth"]["app_token"]
    logger.info("Starting Socket-mode handler.")
    ws = args.workspace
    SocketModeHandler(app, app_token).start()


# Initialize
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Store Slack events in local database")
    parser.add_argument("workspace", action="store", help="Slack Workspace")
    args = parser.parse_args()
    init(args)


@app.event("message")
def handle_message_events(event, say):
    global ws
    user = event["user"]
    ts = event["ts"]
    text = event["text"]
    channel_type = event["channel_type"]
    channel = event["channel"]
    print(f"ts:           {ts}")
    print(f"user ID:      {user}")
    print(f"channel_type: {channel_type}")
    print(f"channel ID:   {channel}")
    print(f"text:         {text}")
    print("")
    if channel_type in ("channel", "group", "im"):
        store_message(ws, event)
        mark_channel_unread(ws, channel)


@app.event("reaction_added")
def handle_reaction_added_events(event):
    reaction = event["reaction"]
    item_type = event["item"]["type"]
    channel = event["item"]["channel"]
    ts = event["item"]["ts"]
    print(f"reaction added: {reaction}")
    print(f"item_type:      {item_type}")
    print(f"channel ID:     {channel}")
    print(f"ts:             {ts}")
    print("")
    if item_type == "message":
        # print(json.dumps(event, indent=4))
        add_reaction(ws, event)


@app.event("reaction_removed")
def handle_all(event, say):
    reaction = event["reaction"]
    item_type = event["item"]["type"]
    channel = event["item"]["channel"]
    ts = event["item"]["ts"]
    print(f"reaction removed: {reaction}")
    print(f"item_type:      {item_type}")
    print(f"channel ID:     {channel}")
    print(f"ts:             {ts}")
    print("")
    if item_type == "message":
        remove_reaction(ws, event)


@app.event("file_shared")
def handle_file_shared_events(event, say):
    print(json.dumps(event, indent=4))


@app.event("file_created")
def handle_file_created_events(event, say):
    print(json.dumps(event, indent=4))


if __name__ == "__main__":
    main(args)
