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


class BadArgument(SentinelError):
    """Raised when a user gives a bad argument to a command"""

    pass


class MissingRequiredArgument(SentinelError):
    """Raised when a user does not provide a required argument to a command"""

    pass


class MissingPermissions(SentinelError):
    """Raised when a user does not have the required permissions to run a command"""

    pass


class BotMissingPermissions(SentinelError):
    """Raised when the bot does not have the required permissions to run a command"""

    pass
