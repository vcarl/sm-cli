"""Command suggestion system with fuzzy matching for typos."""

__all__ = [
    "levenshtein_distance",
    "find_similar_commands",
    "get_all_valid_commands",
    "suggest_command",
]


def levenshtein_distance(s1, s2):
    """Calculate Levenshtein (edit) distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar_commands(unknown, candidates, threshold=3):
    """
    Find commands similar to 'unknown' within edit distance threshold.

    Returns a list of (command, distance) tuples, sorted by distance.
    """
    matches = []
    for cmd in candidates:
        dist = levenshtein_distance(unknown.lower(), cmd.lower())
        if dist <= threshold:
            matches.append((cmd, dist))

    # Sort by distance, then alphabetically
    matches.sort(key=lambda x: (x[1], x[0]))
    return matches


def get_all_valid_commands():
    """
    Collect all valid command names from COMMAND_MAP and ENDPOINT_ARGS.

    Returns a set of command names (with hyphens, as users type them).
    """
    from spacemolt.cli import COMMAND_MAP
    from spacemolt.commands.passthrough import ENDPOINT_ARGS

    valid = set(COMMAND_MAP.keys())

    # Add all passthrough endpoints (convert underscores to hyphens)
    for endpoint in ENDPOINT_ARGS.keys():
        valid.add(endpoint.replace("_", "-"))

    return valid


def suggest_command(unknown):
    """
    Generate a suggestion message for an unknown command.

    Returns a string with suggestions, or None if no good matches found.
    """
    all_commands = get_all_valid_commands()
    similar = find_similar_commands(unknown, all_commands, threshold=3)

    if not similar:
        return None

    if len(similar) == 1:
        cmd, _ = similar[0]
        return f"Did you mean '{cmd}'?"
    elif len(similar) <= 3:
        # Show up to 3 suggestions
        cmd_list = ", ".join(f"'{cmd}'" for cmd, _ in similar)
        return f"Did you mean one of these?\n  {cmd_list}"
    else:
        # Too many matches, just show the top 3
        top_3 = similar[:3]
        cmd_list = ", ".join(f"'{cmd}'" for cmd, _ in top_3)
        return f"Did you mean one of these?\n  {cmd_list}"
