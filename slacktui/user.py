import httpx


def query_users(config):
    """
    Generator queries users and produces entries corresponding to each one.
    """
    url = "https://slack.com/api/users.list"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"types": "public_channel,private_channel"}
    response = httpx.get(url, headers=headers, params=params)
    json_response = response.json()
    try:
        users = json_response["members"]
    except KeyError:
        raise
    for user in users:
        yield user


def get_authenticated_user(config):
    """
    Gets the authenticated user's identity.
    """
    url = "https://slack.com/api/auth.test"
    user_token = config["oauth"]["user_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    response = httpx.get(url, headers=headers)
    if response.status_code != 200:
        print(
            f"Received HTTP status {response.status_code} while trying to"
            " fetch the authenticated user's identity record."
        )
    json_response = response.json()
    return json_response
