import pathlib

import tomllib


def load_config(workspace):
    """
    Load config.
    """
    pth = pathlib.Path(f"~/.config/slacktui/{workspace}.toml").expanduser()
    with open(pth, "rb") as f:
        config = tomllib.load(f)
    return config
