from typing import Final
import re

WOLFRAM_API_URL: Final[str] = "http://api.wolframalpha.com/v1/result"
READTHEDOCS_URL: Final[str] = "https://readthedocs.org/projects/search"

CATCH_COMMAND_ERRORS: Final[bool] = False
DEFAULT_PREFIX: Final[str] = ">>"
RESERVED_TAG_NAMES: Final[list[str]] = [
    "tag",
    "tags",
    "alias",
    "info",
    "search",
    "create",
    "edit",
    "del",
    "delete",
    "new",
    "remove",
]
TAG_NAME_REGEX: Final[re.Pattern] = re.compile(r"^[A-z0-9_]{3,32}$")
