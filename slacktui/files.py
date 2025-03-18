from slacktui.database import load_file, store_file
import httpx


def get_file_data(config, workspace, file_id):
    data = load_file(workspace, file_id)
    if data is not None:
        return data
    # File not in local database.
    # It must be retrieved.
    user_token = config["oauth"]["user_token"]
    params = {"file": file_id}
    headers = {"Authorization": f"Bearer {user_token}"}
    url = "https://slack.com/api/files.info"
    r = httpx.get(url, params=params, headers=headers)
    if r.status_code != 200:
        return None
    json_response = r.json()
    try:
        file_metadata = json_response["file"]
    except KeyError:
        raise
    private_url = file_metadata["url_private"]
    r = httpx.get(private_url, headers=headers)
    if r.status_code != 200:
        return None
    timestamp = file_metadata["created"]
    name = file_metadata["name"]
    mimetype = file_metadata["mimetype"]
    title = file_metadata.get("title")
    file_data = r.content
    store_file(
        workspace,
        file_id,
        file_data,
        name,
        timestamp=timestamp,
        title=title,
        mimetype=mimetype,
    )
    return file_data
