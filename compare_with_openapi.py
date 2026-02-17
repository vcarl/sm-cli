#!/usr/bin/env python3
"""
Compare the analyzed API usage against an OpenAPI spec.
Identifies:
- Endpoints used by client but not in spec
- Endpoints in spec but never used by client
- Request body mismatches
- Response field usage vs spec definitions
"""
import json
import sys
from pathlib import Path


def load_openapi_spec(spec_path):
    """Load and parse OpenAPI spec."""
    with open(spec_path) as f:
        if spec_path.endswith('.yaml') or spec_path.endswith('.yml'):
            try:
                import yaml
                return yaml.safe_load(f)
            except ImportError:
                print("⚠️  PyYAML not installed. Install with: pip install pyyaml")
                sys.exit(1)
        else:
            return json.load(f)


def extract_openapi_endpoints(spec):
    """Extract endpoint information from OpenAPI spec."""
    endpoints = {}
    paths = spec.get('paths', {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                continue

            # OpenAPI paths like /api/v1/get_status -> get_status
            # Normalize to match client usage
            endpoint_name = path.strip('/').split('/')[-1]

            # Extract request body schema
            request_body = None
            if 'requestBody' in details:
                content = details['requestBody'].get('content', {})
                json_content = content.get('application/json', {})
                schema = json_content.get('schema', {})
                request_body = extract_schema_properties(schema, spec)

            # Extract response schema
            responses = details.get('responses', {})
            response_200 = responses.get('200', {})
            response_content = response_200.get('content', {})
            response_json = response_content.get('application/json', {})
            response_schema = response_json.get('schema', {})
            response_fields = extract_schema_properties(response_schema, spec, prefix='')

            endpoints[endpoint_name] = {
                'path': path,
                'method': method.upper(),
                'request_body': request_body,
                'response_fields': response_fields,
                'description': details.get('summary') or details.get('description', '')
            }

    return endpoints


def extract_schema_properties(schema, spec, prefix=''):
    """Recursively extract properties from JSON schema."""
    properties = {}

    # Handle $ref
    if '$ref' in schema:
        ref_path = schema['$ref'].split('/')
        ref_schema = spec
        for part in ref_path:
            if part == '#':
                continue
            ref_schema = ref_schema.get(part, {})
        return extract_schema_properties(ref_schema, spec, prefix)

    # Handle object properties
    if 'properties' in schema:
        for prop_name, prop_schema in schema['properties'].items():
            full_name = f"{prefix}.{prop_name}" if prefix else prop_name
            prop_type = prop_schema.get('type', 'unknown')

            # Recurse into nested objects
            if prop_type == 'object' or 'properties' in prop_schema:
                nested = extract_schema_properties(prop_schema, spec, full_name)
                properties.update(nested)
            else:
                properties[full_name] = {
                    'type': prop_type,
                    'required': prop_name in schema.get('required', [])
                }

    # Handle allOf, oneOf, anyOf
    for combiner in ['allOf', 'oneOf', 'anyOf']:
        if combiner in schema:
            for sub_schema in schema[combiner]:
                nested = extract_schema_properties(sub_schema, spec, prefix)
                properties.update(nested)

    return properties


def compare_endpoints(client_usage, openapi_spec):
    """Compare client endpoint usage against OpenAPI spec."""
    client_endpoints = set(client_usage['endpoints'].keys())
    spec_endpoints = set(openapi_spec.keys())

    # Filter out dynamic/variable endpoints
    client_static = {e for e in client_endpoints if not e.startswith('<')}

    missing_from_spec = client_static - spec_endpoints
    unused_in_client = spec_endpoints - client_static
    matched = client_static & spec_endpoints

    return {
        'missing_from_spec': sorted(missing_from_spec),
        'unused_in_client': sorted(unused_in_client),
        'matched': sorted(matched)
    }


def compare_request_bodies(client_endpoint, spec_endpoint):
    """Compare request body structure."""
    client_body = client_endpoint.get('merged_body', {})
    spec_body = spec_endpoint.get('request_body', {})

    if not client_body and not spec_body:
        return {'status': 'ok', 'issues': []}

    issues = []

    # Check for fields used by client but not in spec
    client_fields = set(client_body.keys()) if isinstance(client_body, dict) else set()
    spec_fields = set(spec_body.keys()) if isinstance(spec_body, dict) else set()

    extra_fields = client_fields - spec_fields
    if extra_fields:
        issues.append(f"Client sends fields not in spec: {', '.join(extra_fields)}")

    # Check for required fields in spec not sent by client
    required_fields = {k for k, v in spec_body.items() if isinstance(v, dict) and v.get('required')}
    missing_required = required_fields - client_fields
    if missing_required:
        issues.append(f"Client missing required fields: {', '.join(missing_required)}")

    status = 'ok' if not issues else 'warning'
    return {'status': status, 'issues': issues}


def compare_response_fields(client_usage, spec_endpoint):
    """Compare response fields accessed by client vs spec definition."""
    # Get all response fields accessed across all files
    all_client_fields = set()
    for fields in client_usage['response_fields_by_file'].values():
        all_client_fields.update(fields)

    spec_fields = set(spec_endpoint.get('response_fields', {}).keys())

    issues = []

    # Fields accessed by client but not in spec
    extra_fields = all_client_fields - spec_fields
    if extra_fields:
        # Only report fields that look like they should be in the spec
        # (filter out generic ones like 'error', 'message')
        significant = {f for f in extra_fields if '.' in f or f not in
                      {'error', 'message', 'success', 'status', 'result', 'data'}}
        if significant:
            issues.append(f"Client accesses fields not in spec: {', '.join(sorted(significant)[:5])}")

    status = 'ok' if not issues else 'info'
    return {'status': status, 'issues': issues, 'extra_count': len(extra_fields)}


def generate_report(client_usage, openapi_spec, output_format='text'):
    """Generate comparison report."""
    endpoint_comparison = compare_endpoints(client_usage, openapi_spec)

    if output_format == 'json':
        report = {
            'summary': {
                'client_endpoints': len([e for e in client_usage['endpoints'].keys() if not e.startswith('<')]),
                'spec_endpoints': len(openapi_spec),
                'matched': len(endpoint_comparison['matched']),
                'missing_from_spec': len(endpoint_comparison['missing_from_spec']),
                'unused_in_client': len(endpoint_comparison['unused_in_client'])
            },
            'endpoint_comparison': endpoint_comparison,
            'detailed_analysis': {}
        }

        # Detailed analysis for matched endpoints
        for endpoint in endpoint_comparison['matched']:
            client_ep = client_usage['endpoints'][endpoint]
            spec_ep = openapi_spec[endpoint]

            body_comparison = compare_request_bodies(client_ep, spec_ep)
            response_comparison = compare_response_fields(client_usage, spec_ep)

            report['detailed_analysis'][endpoint] = {
                'request_body': body_comparison,
                'response_fields': response_comparison
            }

        print(json.dumps(report, indent=2))

    else:  # text format
        print("=" * 80)
        print("API COMPATIBILITY REPORT")
        print("=" * 80)

        print(f"\n📊 Summary:")
        print(f"   • Client uses {len([e for e in client_usage['endpoints'].keys() if not e.startswith('<')])} endpoints")
        print(f"   • OpenAPI spec defines {len(openapi_spec)} endpoints")
        print(f"   • Matched: {len(endpoint_comparison['matched'])}")
        print(f"   • Client uses but not in spec: {len(endpoint_comparison['missing_from_spec'])}")
        print(f"   • Spec defines but client never uses: {len(endpoint_comparison['unused_in_client'])}")

        if endpoint_comparison['missing_from_spec']:
            print(f"\n⚠️  Endpoints used by client but NOT in OpenAPI spec:")
            for ep in endpoint_comparison['missing_from_spec']:
                print(f"   • {ep}")

        if endpoint_comparison['unused_in_client']:
            print(f"\n💡 Endpoints in spec but never used by client:")
            for ep in endpoint_comparison['unused_in_client'][:10]:
                print(f"   • {ep}")
            if len(endpoint_comparison['unused_in_client']) > 10:
                print(f"   ... and {len(endpoint_comparison['unused_in_client']) - 10} more")

        print("\n" + "=" * 80)
        print("DETAILED ENDPOINT ANALYSIS")
        print("=" * 80)

        issues_found = False
        for endpoint in sorted(endpoint_comparison['matched']):
            client_ep = client_usage['endpoints'][endpoint]
            spec_ep = openapi_spec[endpoint]

            body_comparison = compare_request_bodies(client_ep, spec_ep)
            response_comparison = compare_response_fields(client_usage, spec_ep)

            has_issues = (body_comparison['issues'] or
                         (response_comparison['issues'] and response_comparison['status'] != 'info'))

            if has_issues:
                issues_found = True
                print(f"\n🔗 {endpoint}")
                if body_comparison['issues']:
                    print(f"   Request Body Issues:")
                    for issue in body_comparison['issues']:
                        print(f"      • {issue}")
                if response_comparison['issues']:
                    print(f"   Response Issues:")
                    for issue in response_comparison['issues']:
                        print(f"      • {issue}")

        if not issues_found:
            print("\n✅ All matched endpoints look compatible!")

        print("\n" + "=" * 80)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Compare API usage analysis with OpenAPI spec'
    )
    parser.add_argument('openapi_spec', help='Path to OpenAPI spec (JSON or YAML)')
    parser.add_argument('--usage', default='./api_usage_analysis.json',
                       help='Path to API usage analysis JSON (default: ./api_usage_analysis.json)')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')

    args = parser.parse_args()

    # Load files
    print(f"📖 Loading OpenAPI spec from {args.openapi_spec}...")
    openapi_data = load_openapi_spec(args.openapi_spec)

    print(f"📖 Loading API usage from {args.usage}...")
    with open(args.usage) as f:
        usage_data = json.load(f)

    print(f"🔍 Analyzing...\n")

    # Extract endpoint info from OpenAPI
    openapi_endpoints = extract_openapi_endpoints(openapi_data)

    # Generate comparison report
    generate_report(usage_data, openapi_endpoints, args.format)
