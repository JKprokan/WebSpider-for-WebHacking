import sqlite3
import json
from collections import Counter, defaultdict
from urllib.parse import urlparse
import re

DB_PATH = "data/crawl_links.db"

def analyze_input_fields():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT input_fields FROM crawl_links WHERE input_fields != '[]'")
    rows = cursor.fetchall()
    conn.close()
    
    field_types = Counter()
    field_names = Counter()
    field_attrs = defaultdict(Counter)
    
    for (input_fields_json,) in rows:
        try:
            fields = json.loads(input_fields_json)
            for field in fields:
                if 'type' in field:
                    field_types[field['type']] += 1
                if 'name' in field:
                    field_names[field['name']] += 1
                for attr, value in field.items():
                    field_attrs[attr][value] += 1
        except json.JSONDecodeError:
            continue
    
    return {
        'field_types': dict(field_types.most_common()),
        'field_names': dict(field_names.most_common()),
        'field_attributes': {
            attr: dict(counter.most_common(10))
            for attr, counter in field_attrs.items()
        }
    }

def analyze_url_patterns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT link, host FROM crawl_links")
    rows = cursor.fetchall()
    conn.close()
    
    extensions = Counter()
    paths = Counter()
    hosts = Counter()
    subdomains = Counter()
    directories = Counter()
    
    for link, host in rows:
        parsed = urlparse(link)
        hosts[host] += 1
        
        parts = host.split('.')
        if len(parts) > 2:
            subdomain = parts[0]
            subdomains[subdomain] += 1
        
        path = parsed.path
        if path and path != '/':
            paths[path] += 1
            
            path_parts = [p for p in path.split('/') if p]
            for part in path_parts:
                directories[part] += 1
            
            if '.' in path:
                ext = path.split('.')[-1].lower()
                if len(ext) <= 5:
                    extensions[ext] += 1
    
    return {
        'extensions': dict(extensions.most_common(20)),
        'paths': dict(paths.most_common(20)),
        'hosts': dict(hosts.most_common()),
        'subdomains': dict(subdomains.most_common()),
        'directories': dict(directories.most_common(30))
    }

def analyze_parameters():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT query_params FROM crawl_links WHERE query_params != '{}' ")
    rows = cursor.fetchall()
    conn.close()
    
    param_names = Counter()
    param_values = defaultdict(Counter)
    
    for (query_params_json,) in rows:
        try:
            params = json.loads(query_params_json)
            for name, value in params.items():
                param_names[name] += 1
                if isinstance(value, str) and len(value) <= 50:
                    param_values[name][value] += 1
        except json.JSONDecodeError:
            continue
    
    return {
        'parameter_names': dict(param_names.most_common()),
        'parameter_values': {
            name: dict(counter.most_common(10))
            for name, counter in param_values.items()
        }
    }

def analyze_depth_statistics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT depth, COUNT(*) as count FROM crawl_links GROUP BY depth ORDER BY depth")
    depth_counts = dict(cursor.fetchall())
    
    cursor.execute("""
        SELECT depth, COUNT(*) as pages_with_inputs
        FROM crawl_links
        WHERE input_fields != '[]'
        GROUP BY depth
        ORDER BY depth
    """)
    depth_inputs = dict(cursor.fetchall())
    
    cursor.execute("""
        SELECT depth, COUNT(*) as pages_with_params
        FROM crawl_links
        WHERE query_params != '{}'
        GROUP BY depth
        ORDER BY depth
    """)
    depth_params = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        'pages_per_depth': depth_counts,
        'inputs_per_depth': depth_inputs,
        'params_per_depth': depth_params
    }

def find_interesting_patterns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT link, input_fields, query_params FROM crawl_links")
    rows = cursor.fetchall()
    conn.close()
    
    suspicious_patterns = {
        'admin_paths': [],
        'upload_forms': [],
        'login_forms': [],
        'search_params': [],
        'id_params': [],
        'debug_params': []
    }
    
    for link, input_fields_json, query_params_json in rows:
        if re.search(r'/(admin|administrator|manage|control|panel|dashboard)/', link, re.I):
            suspicious_patterns['admin_paths'].append(link)
        
        try:
            fields = json.loads(input_fields_json)
            for field in fields:
                field_type = field.get('type', '').lower()
                field_name = field.get('name', '').lower()
                
                if field_type == 'file':
                    suspicious_patterns['upload_forms'].append(link)
                
                if any(keyword in field_name for keyword in ['password', 'login', 'user', 'email']):
                    suspicious_patterns['login_forms'].append(link)
            
            params = json.loads(query_params_json)
            for param_name in params.keys():
                param_lower = param_name.lower()
                
                if 'search' in param_lower or 'query' in param_lower:
                    suspicious_patterns['search_params'].append(f"{link}?{param_name}")
                
                if param_lower in ['id', 'user_id', 'uid', 'pid']:
                    suspicious_patterns['id_params'].append(f"{link}?{param_name}")
                
                if param_lower in ['debug', 'test', 'dev', 'verbose']:
                    suspicious_patterns['debug_params'].append(f"{link}?{param_name}")
                    
        except json.JSONDecodeError:
            continue
 
    for key in suspicious_patterns:
        suspicious_patterns[key] = list(set(suspicious_patterns[key]))
    
    return suspicious_patterns

def generate_frequency_report():
    print("\n" + "="*80)
    print("FREQUENCY ANALYSIS REPORT")
    print("="*80)
    
    input_analysis = analyze_input_fields()
    print("\nINPUT FIELDS ANALYSIS")
    print("-" * 40)
    print("Top Field Types:")
    for field_type, count in list(input_analysis['field_types'].items())[:10]:
        print(f"  {field_type}: {count}")
    
    print("\nTop Field Names:")
    for field_name, count in list(input_analysis['field_names'].items())[:10]:
        print(f"  {field_name}: {count}")
 
    url_analysis = analyze_url_patterns()
    print("\nURL PATTERNS ANALYSIS")
    print("-" * 40)
    print("Top Extensions:")
    for ext, count in list(url_analysis['extensions'].items())[:10]:
        print(f"  .{ext}: {count}")
    
    print("\nTop Subdomains:")
    for subdomain, count in list(url_analysis['subdomains'].items())[:10]:
        print(f"  {subdomain}: {count}")
 
    param_analysis = analyze_parameters()
    print("\nPARAMETERS ANALYSIS")
    print("-" * 40)
    print("Top Parameter Names:")
    for param, count in list(param_analysis['parameter_names'].items())[:10]:
        print(f"  {param}: {count}")
 
    depth_stats = analyze_depth_statistics()
    print("\nDEPTH STATISTICS")
    print("-" * 40)
    for depth, count in depth_stats['pages_per_depth'].items():
        inputs = depth_stats['inputs_per_depth'].get(depth, 0)
        params = depth_stats['params_per_depth'].get(depth, 0)
        print(f"  Depth {depth}: {count} pages ({inputs} with inputs, {params} with params)")
  
    patterns = find_interesting_patterns()
    print("\nINTERESTING PATTERNS")
    print("-" * 40)
    for pattern_type, urls in patterns.items():
        if urls:
            print(f"{pattern_type.replace('_', ' ').title()}: {len(urls)} found")
            for url in urls[:3]:  
                print(f"  - {url}")
            if len(urls) > 3:
                print(f"  ... and {len(urls) - 3} more")
    
    return {
        'input_fields': input_analysis,
        'url_patterns': url_analysis,
        'parameters': param_analysis,
        'depth_statistics': depth_stats,
        'interesting_patterns': patterns
    }
