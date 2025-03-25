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
        cursor.execute(sql_create_emojis_table)
        conn.commit()


def fetchrows(cursor, num_rows=None, row_wrapper=None):
    """
    Fetch rows in batches of size `num_rows` and yield those.
    """
    if num_rows is None:
        num_rows = cursor.arraysize
    columns = get_columns_from_cursor(cursor)
    while True:
        rows = cursor.fetchmany(num_rows)
        if not rows:
            break
        for row in rows:
            if row_wrapper is not None:
                row = row_wrapper(columns, row)
            yield row


def row2dict(columns, row):
    """
    Wrap a tuple row iterator as a dictionary.
    """
    d = {}
    for n, column_name in enumerate(columns):
        d[column_name] = row[n]
    return d


def get_columns_from_cursor(cursor):
    columns = list(entry[0] for entry in cursor.description)
    return columns


def load_file(workspace, file_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_file, {"file_id": file_id})
        columns = get_columns_from_cursor(cursor)
        row = cursor.fetchone()
        if row is None:
            return None
        return row2dict(columns, row)


def load_channels(workspace, load_dms=False):
    is_channel = True
    is_im = False
    if load_dms:
        is_channel = False
        is_im = True
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_channels, {"is_channel": is_channel, "is_im": is_im})
        for row in fetchrows(cursor):
            yield row


def load_channel(workspace, channel_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_channel, {"channel_id": channel_id})
        columns = get_columns_from_cursor(cursor)
        row = cursor.fetchone()
        if row is None:
            return None
        return row2dict(columns, row)


def load_user(workspace, user_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_user, {"user_id": user_id})
        columns = get_columns_from_cursor(cursor)
        row = cursor.fetchone()
        if row is None:
            return None
        return row2dict(columns, row)


def load_users(workspace):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_users)
        for row in fetchrows(cursor, row_wrapper=row2dict):
            yield row


def load_messages(workspace, channel_id=None):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_load_messages, {"channel_id": channel_id})
        for row in fetchrows(cursor, row_wrapper=row2dict):
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
            {
                "ts": ts,
                "channel_id": channel_id,
                "message_json": message_json,
            },
        )


def mark_channel_read(workspace, channel_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        print(f"Marking channel {channel_id} read ...")
        print(f"SQL: {sql_update_channel_read_status}")
        read = True
        cursor.execute(
            sql_update_channel_read_status, {"channel_id": channel_id, "read": read}
        )
        conn.commit()


def mark_channel_unread(workspace, channel_id):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        print(f"Marking channel {channel_id} read ...")
        print(f"SQL: {sql_update_channel_read_status}")
        read = False
        cursor.execute(
            sql_update_channel_read_status, {"channel_id": channel_id, "read": read}
        )
        conn.commit()


def add_reaction(workspace, event):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        ts = event["item"]["ts"]
        channel_id = event["item"]["channel"]
        cursor.execute(sql_load_message, {"channel_id": channel_id, "ts": ts})
        row = cursor.fetchone()
        if row is None:
            return
        message = json.loads(row[0])
        reactions = message.setdefault("reactions", [])
        added_reaction = event["reaction"]
        updated = False
        for reaction in reactions:
            name = reaction["name"]
            if name == added_reaction:
                count = reaction["count"]
                reaction["count"] = count + 1
                updated = True
                break
        if not updated:
            reaction = {
                "name": added_reaction,
                "users": [],
                "count": 1,
            }
            reactions.append(reaction)
    store_message(workspace, message)


def remove_reaction(workspace, event):
    path = get_db_path(workspace)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        ts = event["item"]["ts"]
        channel_id = event["item"]["channel"]
        cursor.execute(sql_load_message, {"channel_id": channel_id, "ts": ts})
        row = cursor.fetchone()
        if row is None:
            return
        message = json.loads(row[0])
        reactions = message.get("reactions")
        if reactions is None:
            return
        removed_reaction = event["reaction"]
        updated = False
        for n, reaction in enumerate(reactions):
            name = reaction["name"]
            if name == removed_reaction:
                count = reaction["count"]
                count -= 1
                reaction["count"] = count
                updated = True
                break
        if updated:
            if count == 0:
                pos = n + 1
                reactions = reactions[:n] + reactions[pos:]
            if len(reactions) == 0:
                del message["reactions"]
            else:
                message["reactions"] = reactions
    store_message(workspace, message)


sql_update_channel_read_status = """\
    UPDATE channels
    SET read = :read
    WHERE id = :channel_id
    """


sql_load_file = """\
    SELECT
        timestamp,
        name,
        title,
        mimetype,
        data
    FROM files
    WHERE id = :file_id
    """


sql_load_message = """\
    SELECT
        json_blob->'$' json_blob
    FROM messages
    WHERE channel_id = :channel_id
    AND ts = :ts
    """


sql_load_messages = """\
    SELECT
        m.ts,
        u.json_blob->>'name' user,
        m.json_blob->'files' files_json,
        m.json_blob->'$' json_blob
    FROM messages m
        INNER JOIN channels c
            ON m.channel_id = c.id
        INNER JOIN users u
            ON u.id = m.json_blob->>'user'
    WHERE c.id = :channel_id
    ORDER BY m.ts
    """


sql_load_channels = """\
    SELECT c.id, c.json_blob->>'name' name, c.json_blob->>'user' user_id, c.read
    FROM channels c
        LEFT OUTER JOIN users u
            ON c.json_blob->>'user' = u.id
            AND c.json_blob->>'is_im' = TRUE
    WHERE (
        (c.json_blob->>'is_channel' = :is_channel)
        OR
        (c.json_blob->>'is_channel' IS NULL AND :is_channel = FALSE)
    )
    AND c.json_blob->>'is_im' = :is_im
    AND COALESCE(u.json_blob->>'deleted', FALSE) = FALSE
    AND COALESCE(u.json_blob->>'is_bot', FALSE) = FALSE
    ORDER BY c.json_blob->>'name'
    """

sql_load_channel = """\
    SELECT
        id,
        json_blob->>'is_channel' is_channel,
        json_blob->>'is_group' is_group,
        json_blob->>'is_im' is_im,
        json_blob->>'is_mpim' is_mpim,
        json_blob->>'is_private' is_private,
        json_blob->>'name' name
    FROM channels
    WHERE id = :channel_id
    """

sql_load_user = """\
    SELECT
        id,
        json_blob->>'deleted' deleted,
        json_blob->>'name' name,
        json_blob->>'$.profile.real_name' real_name,
        json_blob->>'$.profile.display_name' display_name,
        json_blob->>'tz' tz,
        json_blob->>'is_admin' is_admin,
        json_blob->>'is_bot' is_bot
    FROM users
    WHERE id = :user_id
    """

sql_load_users = """\
    SELECT
        id,
        json_blob->>'name' name,
        json_blob->>'$.profile.display_name' display_name
    FROM users
    ORDER by json_blob->>'name'
    """

sql_insert_file = """\
    INSERT INTO files(id, timestamp, name, title, mimetype, data)
        VALUES(:file_id, :timestamp, :name, :title, :mimetype, :data)
    ON CONFLICT(id) DO UPDATE SET
        timestamp = :timestamp,
        name = :name,
        title = :title,
        mimetype = :mimetype,
        data = :data
    """

sql_insert_message = """\
    INSERT INTO messages (channel_id, ts, json_blob)
        VALUES (:channel_id, :ts, jsonb(:message_json))
    ON CONFLICT(channel_id, ts) DO UPDATE SET json_blob = jsonb(:message_json)
    """

sql_insert_user = """\
    INSERT INTO users(id, json_blob)
        VALUES (:user_id, jsonb(:user_json))
    ON CONFLICT(id) DO UPDATE SET json_blob = jsonb(:user_json)
    """

sql_insert_channel = """\
    INSERT INTO channels(id, read, json_blob)
        VALUES (:channel_id, FALSE, jsonb(:channel_json))
    ON CONFLICT(id) DO UPDATE SET json_blob = jsonb(:channel_json)
    """


sql_create_channels_table = """\
    CREATE TABLE IF NOT EXISTS channels (
        id TEXT,
        read INTEGER,
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

sql_create_emojis_table = """\
    CREATE TABLE IF NOT EXISTS emojis (
        short_code TEXT,
        unified TEXT,
        PRIMARY KEY(short_code)
    )
    """
