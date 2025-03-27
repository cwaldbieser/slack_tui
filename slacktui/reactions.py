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
