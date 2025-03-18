import json
import pathlib
import sqlite3


def get_db_path(workspace):
    path = pathlib.Path(f"~/.config/slacktui/{workspace}.db").expanduser()
    return path


def init_db(workspace):
    """
    Initialize the DB.
    """
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_create_channels_table)
        cursor.execute(sql_create_users_table)
        cursor.execute(sql_create_messages_table)
        cursor.execute(sql_create_files_table)
        conn.commit()


def fetchrows(cursor, num_rows=None, row_wrapper=None):
    """
    Fetch rows in batches of size `num_rows` and yield those.
    """
    if num_rows is None:
        num_rows = cursor.arraysize
    columns = list(entry[0] for entry in cursor.description)
    while True:
        rows = cursor.fetchmany(num_rows)
        if not rows:
            break
        for row in rows:
            if row_wrapper is not None:
                row = row_wrapper(columns, row)
            yield row


def load_file(workspace, file_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_file, {"file_id": file_id})
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]


def load_channels(workspace):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_channels)
        for row in fetchrows(cursor):
            yield row


def load_messages(workspace, channel):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_messages, {"channel": channel})
        for row in fetchrows(cursor):
            yield row


def store_file(
    workspace, file_id, data, name, timestamp=None, title=None, mimetype=None
):
    if title is None:
        title = name
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        params = {
            "file_id": file_id,
            "data": data,
            "name": name,
            "timestamp": timestamp,
            "title": title,
            "mimetype": mimetype,
        }
        cursor.execute(sql_insert_file, params)


def store_channels(workspace, channels):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        for channel in channels:
            channel_id = channel["id"]
            channel_json = json.dumps(channel)
            cursor.execute(
                sql_insert_channel,
                {"channel_id": channel_id, "channel_json": channel_json},
            )
        conn.commit()


def store_users(workspace, users):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        for user in users:
            user_id = user["id"]
            user_json = json.dumps(user)
            cursor.execute(
                sql_insert_user,
                {"user_id": user_id, "user_json": user_json},
            )
        conn.commit()


def store_message(workspace, message):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        ts = message["ts"]
        channel_id = message["channel"]
        message_json = json.dumps(message)
        cursor.execute(
            sql_insert_message,
            {"ts": ts, "channel_id": channel_id, "message_json": message_json},
        )
        conn.commit()


sql_load_file = """\
    SELECT data
    FROM files
    WHERE id = :file_id
    """


sql_load_messages = """\
    SELECT
        m.ts,
        u.json_blob->>'name' user,
        m.json_blob->>'text' text,
        m.json_blob->'files' files_json
    FROM messages m
        INNER JOIN channels c
            ON m.channel_id = c.id
        INNER JOIN users u
            ON u.id = m.json_blob->>'user'
    WHERE c.json_blob->>'name' = :channel
    ORDER BY m.ts
    """


sql_load_channels = """\
    SELECT id, json_blob->>'name' name
    FROM channels
    WHERE json_blob->>'is_channel' = 1
    ORDER BY json_blob->>'name'
    """

sql_insert_file = """\
    INSERT OR REPLACE INTO files(id, timestamp, name, title, mimetype, data)
        VALUES(:file_id, :timestamp, :name, :title, :mimetype, :data)
    """

sql_insert_message = """\
    INSERT INTO messages (channel_id, ts, json_blob)
        VALUES (:channel_id, :ts, jsonb(:message_json))
    """

sql_insert_user = """\
    INSERT OR IGNORE INTO users(id, json_blob)
        VALUES (:user_id, jsonb(:user_json))
    """

sql_insert_channel = """\
    INSERT OR IGNORE INTO channels(id, json_blob)
        VALUES (:channel_id, jsonb(:channel_json))
    """


sql_create_channels_table = """\
    CREATE TABLE IF NOT EXISTS channels (
        id TEXT,
        json_blob BLOB,
        PRIMARY KEY (id)
    )
    """

sql_create_users_table = """\
    CREATE TABLE IF NOT EXISTS users (
        id TEXT,
        json_blob BLOB,
        PRIMARY KEY (id)
    )
    """

sql_create_messages_table = """\
    CREATE TABLE IF NOT EXISTS messages (
       channel_id TEXT REFERENCES channels(id) ON DELETE CASCADE,
       ts TEXT,
       json_blob BLOB,
       PRIMARY KEY (channel_id, ts)
    )
    """

sql_create_files_table = """\
    CREATE TABLE IF NOT EXISTS files (
        id TEXT,
        timestamp TEXT,
        name TEXT,
        title TEXT,
        mimetype TEXT,
        data BLOB,
        PRIMARY KEY (id)
    )
    """
