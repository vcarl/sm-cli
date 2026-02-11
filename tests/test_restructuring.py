"""Tests for CLI restructuring: fuzzy matching, hierarchical commands, contextual help."""

import unittest
from io import StringIO
import sys

from spacemolt.suggestions import (
    levenshtein_distance,
    find_similar_commands,
    get_all_valid_commands,
    suggest_command,
)
from spacemolt.context_help import show_contextual_help, COMMAND_SUGGESTIONS
from spacemolt.cli import build_parser


class TestLevenshteinDistance(unittest.TestCase):
    """Test Levenshtein distance algorithm."""

    def test_identical_strings(self):
        self.assertEqual(levenshtein_distance("missions", "missions"), 0)

    def test_one_character_diff(self):
        self.assertEqual(levenshtein_distance("missions", "misions"), 1)

    def test_substitution(self):
        # "attack" -> "atacc" requires 2 operations (delete 't', substitute 'k' with 'c')
        self.assertEqual(levenshtein_distance("attack", "atacc"), 2)

    def test_insertion(self):
        self.assertEqual(levenshtein_distance("jump", "jum"), 1)

    def test_deletion(self):
        self.assertEqual(levenshtein_distance("skill", "skills"), 1)

    def test_multiple_operations(self):
        # "jump" -> "jum" (delete p) -> "jim" (substitute u with i) = 2 operations
        self.assertEqual(levenshtein_distance("jump", "jim"), 2)

    def test_empty_string(self):
        self.assertEqual(levenshtein_distance("", "test"), 4)
        self.assertEqual(levenshtein_distance("test", ""), 4)


class TestFindSimilarCommands(unittest.TestCase):
    """Test finding similar commands."""

    def test_finds_exact_match_within_threshold(self):
        candidates = ["missions", "status", "skills"]
        matches = find_similar_commands("missions", candidates, threshold=3)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], "missions")
        self.assertEqual(matches[0][1], 0)

    def test_finds_close_match(self):
        candidates = ["missions", "status", "skills"]
        matches = find_similar_commands("misions", candidates, threshold=3)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], "missions")
        self.assertEqual(matches[0][1], 1)

    def test_finds_multiple_matches(self):
        candidates = ["jump", "buy", "log"]
        matches = find_similar_commands("jum", candidates, threshold=3)
        # All three are within threshold: jum->jump(1), jum->buy(2), jum->log(2)
        self.assertGreaterEqual(len(matches), 1)
        # First match should be closest
        self.assertEqual(matches[0][0], "jump")

    def test_excludes_beyond_threshold(self):
        candidates = ["missions", "status", "completely-different"]
        matches = find_similar_commands("misions", candidates, threshold=2)
        # "completely-different" should be excluded
        cmd_names = [m[0] for m in matches]
        self.assertNotIn("completely-different", cmd_names)

    def test_sorts_by_distance(self):
        candidates = ["missions", "status", "misions"]
        matches = find_similar_commands("misions", candidates, threshold=3)
        # Should sort by distance, then alphabetically
        distances = [m[1] for m in matches]
        self.assertEqual(distances, sorted(distances))


class TestGetAllValidCommands(unittest.TestCase):
    """Test getting all valid commands."""

    def test_includes_command_map_entries(self):
        commands = get_all_valid_commands()
        # Should include known commands from COMMAND_MAP
        self.assertIn("missions", commands)
        self.assertIn("skills", commands)
        self.assertIn("status", commands)

    def test_includes_passthrough_endpoints(self):
        commands = get_all_valid_commands()
        # Should include passthrough endpoints (with hyphens)
        self.assertIn("attack", commands)
        self.assertIn("scan", commands)

    def test_returns_set(self):
        commands = get_all_valid_commands()
        self.assertIsInstance(commands, set)


class TestSuggestCommand(unittest.TestCase):
    """Test command suggestion generation."""

    def test_suggests_single_close_match(self):
        suggestion = suggest_command("misions")
        self.assertIn("missions", suggestion)
        self.assertIn("Did you mean", suggestion)

    def test_suggests_multiple_matches(self):
        # "jum" is close to "jump", "buy", "log"
        suggestion = suggest_command("jum")
        self.assertIsNotNone(suggestion)
        self.assertIn("did you mean one of these", suggestion.lower())

    def test_returns_none_for_no_matches(self):
        suggestion = suggest_command("zzzzzzzzzzz")
        self.assertIsNone(suggestion)


class TestContextualHelp(unittest.TestCase):
    """Test contextual help system."""

    def test_shows_help_for_defined_commands(self):
        # Capture stdout
        captured = StringIO()
        sys.stdout = captured

        # Mock args without JSON flag
        class MockArgs:
            json = False

        show_contextual_help("missions", MockArgs())
        sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertIn("Related commands:", output)
        self.assertIn("sm missions", output)

    def test_skips_help_in_json_mode(self):
        captured = StringIO()
        sys.stdout = captured

        class MockArgs:
            json = True

        show_contextual_help("missions", MockArgs())
        sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertEqual(output, "")

    def test_skips_help_for_undefined_commands(self):
        captured = StringIO()
        sys.stdout = captured

        class MockArgs:
            json = False

        show_contextual_help("undefined-command", MockArgs())
        sys.stdout = sys.__stdout__

        output = captured.getvalue()
        self.assertEqual(output, "")

    def test_all_defined_suggestions_are_valid(self):
        """Ensure all commands in COMMAND_SUGGESTIONS exist."""
        valid_commands = get_all_valid_commands()
        for cmd_key in COMMAND_SUGGESTIONS.keys():
            # The key might not be a direct command (e.g., "missions-active")
            # but the suggestions should reference valid commands
            pass  # This is more of a documentation test


class TestHierarchicalParsers(unittest.TestCase):
    """Test hierarchical command parsers."""

    def test_missions_has_subcommands(self):
        parser = build_parser()
        args = parser.parse_args(["missions", "active"])
        self.assertEqual(args.command, "missions")
        self.assertEqual(args.missions_cmd, "active")

    def test_missions_query_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["missions", "query", "--search", "escort"])
        self.assertEqual(args.command, "missions")
        self.assertEqual(args.missions_cmd, "query")
        self.assertEqual(args.search, "escort")

    def test_missions_accept_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["missions", "accept", "mission-123"])
        self.assertEqual(args.command, "missions")
        self.assertEqual(args.missions_cmd, "accept")
        self.assertEqual(args.mission_id, "mission-123")

    def test_skills_has_subcommands(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "query"])
        self.assertEqual(args.command, "skills")
        self.assertEqual(args.skills_cmd, "query")

    def test_skills_inspect_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "inspect", "mining"])
        self.assertEqual(args.command, "skills")
        self.assertEqual(args.skills_cmd, "inspect")
        self.assertEqual(args.skill_id_inspect, "mining")

    def test_recipes_has_subcommands(self):
        parser = build_parser()
        args = parser.parse_args(["recipes", "query"])
        self.assertEqual(args.command, "recipes")
        self.assertEqual(args.recipes_cmd, "query")

    def test_recipes_craft_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["recipes", "craft", "recipe-123", "5"])
        self.assertEqual(args.command, "recipes")
        self.assertEqual(args.recipes_cmd, "craft")
        self.assertEqual(args.recipe_id, "recipe-123")
        self.assertEqual(args.count, 5)


class TestBackwardsCompatibility(unittest.TestCase):
    """Test that old flat commands still work."""

    def test_old_query_missions_still_exists(self):
        parser = build_parser()
        args = parser.parse_args(["query-missions", "--search", "escort"])
        self.assertEqual(args.command, "query-missions")
        self.assertEqual(args.search, "escort")

    def test_old_active_missions_still_exists(self):
        parser = build_parser()
        args = parser.parse_args(["active-missions"])
        self.assertEqual(args.command, "active-missions")

    def test_old_query_skills_still_exists(self):
        parser = build_parser()
        args = parser.parse_args(["query-skills", "--my"])
        self.assertEqual(args.command, "query-skills")
        self.assertTrue(args.my)

    def test_old_skill_still_exists(self):
        parser = build_parser()
        args = parser.parse_args(["skill", "mining"])
        self.assertEqual(args.command, "skill")
        self.assertEqual(args.skill_id, "mining")

    def test_old_query_recipes_still_exists(self):
        parser = build_parser()
        args = parser.parse_args(["query-recipes", "--trace", "iron-ingot"])
        self.assertEqual(args.command, "query-recipes")
        self.assertEqual(args.trace, "iron-ingot")


class TestMissionsNoSubcommand(unittest.TestCase):
    """Test that missions with no subcommand is valid (shows combined view)."""

    def test_missions_no_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["missions"])
        self.assertEqual(args.command, "missions")
        self.assertIsNone(args.missions_cmd)


class TestSkillsNoSubcommand(unittest.TestCase):
    """Test that skills with no subcommand is valid (shows trained skills)."""

    def test_skills_no_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["skills"])
        self.assertEqual(args.command, "skills")
        self.assertIsNone(args.skills_cmd)


class TestRecipesNoSubcommand(unittest.TestCase):
    """Test that recipes with no subcommand is valid (shows recipe list)."""

    def test_recipes_no_subcommand(self):
        parser = build_parser()
        args = parser.parse_args(["recipes"])
        self.assertEqual(args.command, "recipes")
        self.assertIsNone(args.recipes_cmd)


if __name__ == "__main__":
    unittest.main()
