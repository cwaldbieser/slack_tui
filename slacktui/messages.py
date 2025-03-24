import datetime
import json

import httpx


def message_transform(message):
    """
    Transform message into a cannonical form
    """
    new_msg = {}
    attribs = ["user", "type", "ts", "text", "blocks", "channel", "files", "reactions"]
    for attrib in attribs:
        value = message.get(attrib)
        if value is not None:
            new_msg[attrib] = value
    blocks = new_msg.get("blocks")
    if blocks is not None:
        for block in blocks:
            if "block_id" in block:
                del block["block_id"]
    return new_msg


def post_message(config, channel_id, text, thread_ts=None):
    """
    Post a text message to a channel.
    """
    url = "https://slack.com/api/chat.postMessage"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "channel": channel_id,
        "text": text,
    }
    if thread_ts:
        params["thread_ts"] = thread_ts
    r = httpx.post(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when posting"
            f" to channel with id {channel_id}.",
        )
        return
    json_response = r.json()
    if "error" in json_response:
        print(json.dumps(json_response, indent=4))


def get_history_for_channel(config, channel_id, days):
    """
    Generator produces `days` days worth of history from the channel specified
    by channel ID.
    """
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/conversations.history"
    ts = (datetime.datetime.today() - datetime.timedelta(days)).timestamp()
    params = {"channel": channel_id, "limit": 100, "oldest": ts}
    for json_response in page_results(httpx.get, url, params=params, headers=headers):
        messages = json_response["messages"]
        messages.reverse()
        for message in messages:
            yield message_transform(message)


def page_results(request_func, url, params, headers):
    """
    Generator pages results for web API requests.
    """
    orig_params = dict(params)
    while True:
        r = request_func(url, params=params, headers=headers)
        r.raise_for_status()
        json_response = r.json()
        yield json_response
        has_more = json_response.get("has_more", False)
        if not has_more:
            break
        response_metadata = json_response["response_metadata"]
        try:
            cursor = response_metadata["next_cursor"]
        except KeyError:
            print(json.dumps(response_metadata, indent=4))
            raise
        params = dict(orig_params)
        params["cursor"] = cursor
