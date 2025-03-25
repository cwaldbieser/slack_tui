#! /usr/bin/env python

import argparse
import pathlib
import sqlite3
import httpx


def main(args):
    """
    main program
    """
    url = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"
    resp = httpx.get(url)
    o = resp.json()
    path = get_db_path(args.workspace)
    sql = """\
        INSERT OR IGNORE INTO emojis(short_code, unified) VALUES (:short_code, :unified)
        """
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        for item in o:
            short_code = item["short_name"]
            unified = item["unified"]
            cursor.execute(sql, {"short_code": short_code, "unified": unified})
    conn.commit()


def get_db_path(workspace):
    path = pathlib.Path(f"~/.config/slacktui/{workspace}.db").expanduser()
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Fetch emoji data and store in local database.")
    parser.add_argument(
        "workspace",
        action="store",
        help="The workspace ID")
    args = parser.parse_args()
    main(args)
