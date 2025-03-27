import json

import httpx


def add_reaction(config, channel_id, ts, reaction):
    """
    Add a reaction to a message.
    """
    url = "https://slack.com/api/reactions.add"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "channel": channel_id,
        "name": reaction,
        "timestamp": ts,
    }
    r = httpx.post(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when reacting"
            f" to channel {channel_id}, ts {ts} with {reaction}.",
        )
        return
    json_response = r.json()
    if "error" in json_response:
        print(json.dumps(json_response, indent=4))


def remove_reaction(config, channel_id, ts, reaction):
    """
    Remove a reaction from a message.
    """
    url = "https://slack.com/api/reactions.remove"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "channel": channel_id,
        "name": reaction,
        "timestamp": ts,
    }
    r = httpx.post(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when removing reaction {reaction}"
            f" from channel {channel_id}, ts {ts}.",
        )
        return
    json_response = r.json()
    if "error" in json_response:
        print(json.dumps(json_response, indent=4))


def fetch_reactions_for_message(config, channel_id, ts):
    """
    Fetch reactions to a message.
    """
    url = "https://slack.com/api/reactions.get"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {
        "channel": channel_id,
        "timestamp": ts,
    }
    r = httpx.post(url, headers=headers, params=params)
    if r.status_code != 200:
        print(
            f"Got status {r.status_code} when fetching reactions for message"
            f" with channel {channel_id}, ts {ts}.",
        )
        return
    json_response = r.json()
    if "error" in json_response:
        print(json.dumps(json_response, indent=4))
    return json_response
