import re

def compile_patterns(pattern_str):
    return [re.compile(p.strip(), re.IGNORECASE) for p in pattern_str.split(",")] if pattern_str else []

def is_url_allowed(url, include_patterns, exclude_patterns):
    if include_patterns and not any(p.search(url) for p in include_patterns):
        return False
    if exclude_patterns and any(p.search(url) for p in exclude_patterns):
        return False
    return True
