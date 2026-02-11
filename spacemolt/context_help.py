"""Contextual help and sibling command suggestions."""

__all__ = ["show_contextual_help", "COMMAND_SUGGESTIONS"]


# Map command names to their related commands
COMMAND_SUGGESTIONS = {
    "missions": [
        "sm missions accept <id>    # Accept a mission",
        "sm missions query          # Search missions",
        "sm missions complete <id>  # Complete mission",
        "sm missions abandon <id>   # Abandon mission",
    ],
    "active-missions": [
        "sm missions complete <id>  # Complete mission",
        "sm missions abandon <id>   # Abandon mission",
    ],
    "query-missions": [
        "sm missions accept <id>    # Accept a mission",
        "sm missions complete <id>  # Complete mission",
    ],
    "skills": [
        "sm skills query            # Search all skills",
        "sm skills inspect <id>     # Deep inspect skill",
    ],
    "query-skills": [
        "sm skills inspect <id>     # Deep inspect skill",
    ],
    "skill": [
        "sm skills query            # Search all skills",
    ],
    "recipes": [
        "sm recipes query           # Search recipes",
        "sm recipes craft <id>      # Craft recipe",
    ],
    "query-recipes": [
        "sm recipes trace <item>    # Ingredient tree",
        "sm recipes craft <id>      # Craft recipe",
    ],
}


def show_contextual_help(command_name, args=None):
    """
    Print contextual help for a command if available.

    Only shows if:
    1. Command has suggestions defined
    2. Not in JSON mode (args.json == False)
    3. Command is in the high-traffic list

    Args:
        command_name: The command name (e.g., "missions", "skills")
        args: The argparse namespace (to check for --json flag)
    """
    # Skip if JSON mode
    if args and getattr(args, "json", False):
        return

    suggestions = COMMAND_SUGGESTIONS.get(command_name)
    if not suggestions:
        return

    print("\nRelated commands:")
    for suggestion in suggestions:
        print(f"  {suggestion}")
