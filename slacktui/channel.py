import httpx


def query_channels(config):
    """
    Generator queries channels and produces entries corresponding to each one.
    """
    url = "https://slack.com/api/conversations.list"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"types": "public_channel,private_channel,mpim,im"}
    response = httpx.get(url, headers=headers, params=params)
    json_response = response.json()
    channels = json_response["channels"]
    for channel in channels:
        yield channel
