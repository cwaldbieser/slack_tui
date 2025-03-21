from rich import inspect
from rich.markup import escape

from slacktui.database import load_channel, load_user


def format_text_item(workspace, item):
    """
    Format a Slack text item.
    Return the formatted text.
    """
    parts = []
    blocks = item.get("blocks", [])
    for block in blocks:
        outer_elements = block["elements"]
        for outer_element in outer_elements:
            element_type = outer_element["type"]
            if element_type == "rich_text_section":
                part = process_rich_text_section(workspace, outer_element)
                parts.append(part)
            if element_type == "rich_text_list":
                part = process_rich_text_list(workspace, outer_element)
                parts.append(part)
    return "".join(parts)


def process_rich_text_section(workspace, element):
    inner_elements = element["elements"]
    parts = []
    for inner_element in inner_elements:
        elm_type = inner_element["type"]
        if elm_type == "text":
            part = format_text_markup(inner_element)
            parts.append(part)
        elif elm_type == "rich_text_section":
            part = process_rich_text_section(workspace, inner_element)
            parts.append(part)
        elif elm_type == "rich_text_list":
            part = process_rich_text_list(workspace, inner_element)
            parts.append(part)
        elif elm_type == "link":
            try:
                link = inner_element["url"]
            except KeyError:
                inspect(inner_element)
                raise
            text = inner_element.get("text", link)
            link = escape(link)
            text = escape(text)
            markup = f"[hyperlink][link={link}]{text} ({link})[/link][/hyperlink]"
            parts.append(markup)
        elif elm_type == "emoji":
            emoji = construct_emoji(inner_element)
            parts.append(emoji)
        elif elm_type == "user":
            user = construct_user(workspace, inner_element)
            parts.append(user)
        elif elm_type == "channel":
            channel = construct_channel(workspace, inner_element)
            parts.append(channel)
    return "".join(parts)


def process_rich_text_list(workspace, element):
    parts = []
    inner_elements = element["elements"]
    for inner_element in inner_elements:
        elm_type = inner_element["type"]
        if elm_type == "rich_text_section":
            part = process_rich_text_section(workspace, inner_element)
            parts.append(part)
    list_text = "\n".join(f"\u25e6 {part}" for part in parts)
    return f"{list_text}\n"


def format_text_markup(inner_element):
    style = inner_element.get("style")
    if style is None:
        return escape(inner_element["text"])
    styles = []
    if style.get("bold", False):
        styles.append("bold")
    if style.get("italic", False):
        styles.append("italic")
    if style.get("strike", False):
        styles.append("strike")
    if len(styles) == 0:
        return escape(inner_element["text"])
    markup = " ".join(styles)
    return f"[{markup}]{escape(inner_element['text'])}[/{markup}]"


def construct_channel(workspace, element):
    """
    Construct a channel from a message element.
    """
    channel_id = element["channel_id"]
    channel_info = load_channel(workspace, channel_id)
    if channel_info is None:
        channel = channel_id
    else:
        channel = channel_info["name"]
    return f"[channel]#{escape(channel)}[/channel]"


def construct_user(workspace, element):
    """
    Construct a user from a message element.
    """
    user_id = element["user_id"]
    user_info = load_user(workspace, user_id)
    if user_info is None:
        username = user_id
    else:
        username = user_info["display_name"]
    return f"[$text-accent]@{escape(username)}[/]"


def construct_emoji(element):
    """
    Construct an emoji from `element`.
    """
    unicode_hex = element.get("unicode")
    if unicode_hex is None:
        return f":{element['name']}:"
    hexes = unicode_hex.split("-")
    parts = [chr(int(code, 16)) for code in hexes]
    return "".join(parts)
