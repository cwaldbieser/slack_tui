#! /usr/bin/env python

import argparse
import json

import logzero
from logzero import logger
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slacktui.channel import query_channels
from slacktui.config import load_config
from slacktui.database import (init_db, store_channels, store_message,
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
    parser = argparse.ArgumentParser("Listen to Slack Channels")
    parser.add_argument("workspace", action="store", help="Slack Workspace")
    args = parser.parse_args()
    init(args)


@app.event("message")
def handle_message_events(event, say):
    global ws
    store_message(ws, event)


@app.event("file_shared")
def handle_file_shared_events(event, say):
    print(json.dumps(event, indent=4))


@app.event("file_created")
def handle_file_created_events(event, say):
    print(json.dumps(event, indent=4))


if __name__ == "__main__":
    main(args)
