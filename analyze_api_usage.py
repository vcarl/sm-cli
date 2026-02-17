#!/usr/bin/env python3
"""
Analyze spacemolt codebase to extract API usage patterns:
- Endpoints called
- Request body structures
- Response fields accessed
"""
import ast
import json
import os
from collections import defaultdict
from pathlib import Path


class APICallVisitor(ast.NodeVisitor):
    """Extract _post() calls and response field accesses."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.api_calls = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Call(self, node):
        # Look for _post() method calls
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == '_post'):

            call_info = {
                'file': self.filepath,
                'line': node.lineno,
                'function': self.current_function,
                'endpoint': self._extract_endpoint(node),
                'body_structure': self._extract_body(node),
                'context': self._get_context_lines(node.lineno)
            }
            self.api_calls.append(call_info)

        self.generic_visit(node)

    def _extract_endpoint(self, node):
        """Extract endpoint from first argument."""
        if len(node.args) == 0:
            return None

        arg = node.args[0]
        if isinstance(arg, ast.Constant):
            return arg.value
        elif isinstance(arg, ast.Str):  # Python 3.7 compat
            return arg.s
        elif isinstance(arg, ast.Name):
            return f"<variable: {arg.id}>"
        elif isinstance(arg, ast.JoinedStr):  # f-string
            return "<f-string>"
        else:
            return f"<{type(arg).__name__}>"

    def _extract_body(self, node):
        """Extract request body structure from second argument."""
        if len(node.args) < 2:
            # Check for body= kwarg
            for kw in node.keywords:
                if kw.arg == 'body':
                    return self._extract_dict_structure(kw.value)
            return None

        body_arg = node.args[1]
        return self._extract_dict_structure(body_arg)

    def _extract_dict_structure(self, node):
        """Extract dictionary structure (keys and value types)."""
        if isinstance(node, ast.Dict):
            structure = {}
            for key, value in zip(node.keys, node.values):
                if key is None:  # **dict unpacking
                    structure['<**unpacked>'] = True
                    continue

                key_name = None
                if isinstance(key, ast.Constant):
                    key_name = key.value
                elif isinstance(key, ast.Str):
                    key_name = key.s

                if key_name:
                    structure[key_name] = self._describe_value(value)
            return structure
        elif isinstance(node, ast.Name):
            return f"<variable: {node.id}>"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"<{node.func.id}()>"
            return "<function call>"
        else:
            return f"<{type(node).__name__}>"

    def _describe_value(self, node):
        """Describe what type/structure a value has."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, (ast.Str, ast.Num)):
            return type(node).__name__.replace('Str', 'str').replace('Num', 'number')
        elif isinstance(node, ast.Name):
            return f"var:{node.id}"
        elif isinstance(node, ast.Dict):
            return self._extract_dict_structure(node)
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"call:{node.func.id}()"
            return "call"
        else:
            return type(node).__name__

    def _get_context_lines(self, lineno):
        """Get a few lines of context around the call."""
        try:
            with open(self.filepath) as f:
                lines = f.readlines()
                start = max(0, lineno - 2)
                end = min(len(lines), lineno + 2)
                context = ''.join(lines[start:end])
                return context.strip()
        except:
            return None


class ResponseFieldVisitor(ast.NodeVisitor):
    """Track .get() calls on variables to understand response structure."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.response_fields = defaultdict(set)
        self.var_tracking = {}  # Track variable assignments

    def visit_Assign(self, node):
        # Track assignments like: result = resp.get("result")
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

            if isinstance(node.value, ast.Call):
                if (isinstance(node.value.func, ast.Attribute) and
                    node.value.func.attr == 'get' and
                    isinstance(node.value.func.value, ast.Name)):

                    source_var = node.value.func.value.id
                    if node.value.args and isinstance(node.value.args[0], (ast.Constant, ast.Str)):
                        field = node.value.args[0].value if isinstance(node.value.args[0], ast.Constant) else node.value.args[0].s
                        self.var_tracking[var_name] = (source_var, field)

        self.generic_visit(node)

    def visit_Call(self, node):
        # Look for .get() calls
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == 'get' and
            isinstance(node.func.value, ast.Name)):

            var_name = node.func.value.id
            if node.args and isinstance(node.args[0], (ast.Constant, ast.Str)):
                field = node.args[0].value if isinstance(node.args[0], ast.Constant) else node.args[0].s

                # Build the path
                path = self._build_path(var_name, field)
                self.response_fields[self.filepath].add(path)

        self.generic_visit(node)

    def _build_path(self, var_name, field):
        """Build dotted path like resp.result.player.credits."""
        path_parts = [field]
        current_var = var_name

        # Walk backwards through variable tracking
        for _ in range(10):  # Prevent infinite loops
            if current_var in self.var_tracking:
                parent_var, parent_field = self.var_tracking[current_var]
                path_parts.insert(0, parent_field)
                current_var = parent_var
            else:
                break

        return '.'.join(path_parts)


def analyze_file(filepath):
    """Analyze a single Python file for API usage."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        # Extract API calls
        call_visitor = APICallVisitor(str(filepath))
        call_visitor.visit(tree)

        # Extract response field accesses
        field_visitor = ResponseFieldVisitor(str(filepath))
        field_visitor.visit(tree)

        return call_visitor.api_calls, field_visitor.response_fields
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {filepath}: {e}")
        return [], {}
    except Exception as e:
        print(f"⚠️  Error analyzing {filepath}: {e}")
        return [], {}


def analyze_codebase(root_dir):
    """Analyze all Python files in the codebase."""
    all_calls = []
    all_response_fields = defaultdict(set)

    for py_file in Path(root_dir).rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        calls, fields = analyze_file(py_file)
        all_calls.extend(calls)

        for file, field_set in fields.items():
            all_response_fields[file].update(field_set)

    return all_calls, all_response_fields


def aggregate_by_endpoint(api_calls):
    """Group API calls by endpoint."""
    by_endpoint = defaultdict(lambda: {
        'calls': [],
        'body_structures': [],
        'files': set()
    })

    for call in api_calls:
        endpoint = call['endpoint']
        if endpoint:
            by_endpoint[endpoint]['calls'].append(call)
            if call['body_structure']:
                by_endpoint[endpoint]['body_structures'].append(call['body_structure'])
            by_endpoint[endpoint]['files'].add(call['file'])

    # Convert sets to lists for JSON serialization
    for endpoint in by_endpoint:
        by_endpoint[endpoint]['files'] = sorted(list(by_endpoint[endpoint]['files']))

    return dict(by_endpoint)


def merge_body_structures(structures):
    """Merge multiple body structures into one representative structure."""
    if not structures:
        return None

    merged = {}
    for struct in structures:
        if isinstance(struct, dict):
            for key, value in struct.items():
                if key not in merged:
                    merged[key] = set() if not isinstance(value, dict) else value
                if not isinstance(merged[key], dict):
                    if isinstance(merged[key], set):
                        merged[key].add(str(value))
                    else:
                        merged[key] = {str(merged[key]), str(value)}

    # Convert sets to lists
    for key in merged:
        if isinstance(merged[key], set):
            merged[key] = sorted(list(merged[key]))

    return merged


def print_report(api_calls, response_fields, output_format='text'):
    """Print analysis report."""

    if output_format == 'json':
        by_endpoint = aggregate_by_endpoint(api_calls)

        # Add merged body structures
        for endpoint, data in by_endpoint.items():
            data['merged_body'] = merge_body_structures(data['body_structures'])
            # Remove the raw list to reduce noise
            del data['body_structures']

        output = {
            'endpoints': by_endpoint,
            'response_fields_by_file': {k: sorted(list(v)) for k, v in response_fields.items()},
            'summary': {
                'total_calls': len(api_calls),
                'unique_endpoints': len(by_endpoint),
                'files_analyzed': len(response_fields)
            }
        }
        print(json.dumps(output, indent=2))

    else:  # text format
        by_endpoint = aggregate_by_endpoint(api_calls)

        print("=" * 80)
        print("API USAGE ANALYSIS")
        print("=" * 80)
        print(f"\n📊 Summary:")
        print(f"   • Total API calls found: {len(api_calls)}")
        print(f"   • Unique endpoints: {len(by_endpoint)}")
        print(f"   • Files analyzed: {len(response_fields)}")

        print("\n" + "=" * 80)
        print("ENDPOINTS & REQUEST STRUCTURES")
        print("=" * 80)

        for endpoint in sorted(by_endpoint.keys()):
            data = by_endpoint[endpoint]
            print(f"\n🔗 {endpoint}")
            print(f"   Calls: {len(data['calls'])}")
            print(f"   Files: {', '.join(os.path.basename(f) for f in data['files'])}")

            merged = merge_body_structures(data['body_structures'])
            if merged:
                print(f"   Request body:")
                for key, value in merged.items():
                    if isinstance(value, list):
                        value_str = ' | '.join(value)
                    else:
                        value_str = str(value)
                    print(f"      • {key}: {value_str}")

            # Show one example call location
            example = data['calls'][0]
            print(f"   Example: {os.path.basename(example['file'])}:{example['line']} in {example['function']}()")

        print("\n" + "=" * 80)
        print("RESPONSE FIELDS ACCESSED")
        print("=" * 80)

        # Aggregate all response fields across files
        all_fields = set()
        for fields in response_fields.values():
            all_fields.update(fields)

        for field in sorted(all_fields):
            print(f"   • {field}")

        print("\n" + "=" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Analyze SpaceMolt API usage patterns')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--dir', default='./spacemolt',
                       help='Directory to analyze (default: ./spacemolt)')

    args = parser.parse_args()

    if args.format != 'json':
        print(f"🔍 Analyzing {args.dir}...\n")

    api_calls, response_fields = analyze_codebase(args.dir)
    print_report(api_calls, response_fields, args.format)
