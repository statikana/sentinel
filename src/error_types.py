from discord.ext.commands import errors as _command_errors


class SentinelError(_command_errors.CommandError):
    pass


class InsufficientBalance(SentinelError):
    """Raised when a user tries to spend more coins than they have"""

    pass


class InvalidAmount(SentinelError):
    """Raised when a user tries to spend a negative amount of coins"""

    pass


class InvalidMember(SentinelError):
    """Raised when a user tries to give/request coins to/from a bot"""

    pass


class InvalidRole(SentinelError):
    """Raised when a user improperly specifies a role"""

    pass


class InvalidChannel(SentinelError):
    """Raised when a user improperly specifies a channel"""

    pass


class TagNameExists(SentinelError):
    """Raised when a user tries to create a tag with a name that already exists"""

    pass


class BadTagName(SentinelError):
    """Raised when a user tries to create a tag with a name that is too long"""

    pass


class BadTagContent(SentinelError):
    """Raised when a user tries to create a tag with content that is too long"""

    pass


class MissingVaguePermissions(SentinelError):
    """Raised when the user doesn't have permissions to do something. This is not a discord permission, but a permission that the bot has set up"""

    pass


class BadUserInput(SentinelError):
    """Raised when a user inputs a user or member that is not valid"""

    pass


BadMemberInput = BadUserInput


class TagNotFound(SentinelError):
    """Raised when a user tries to get, edit, or delete a tag that doesn't exist"""

    pass


class ComponentNotFound(SentinelError):
    """Raised when a user tries to fetch a component that doesn't exist"""

    pass


class MissingPermissions(SentinelError):
    """Raised when a user doesn't have permissions to do something"""

    pass
