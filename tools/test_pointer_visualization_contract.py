#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'tools'))

from exercise_validator import pointer_trace_shape_issues, validate_timeline_integrity
from generate_exercise import normalize_hidden_runtime_artifact

source = (PROJECT_ROOT / 'tools/generate_exercise.py').read_text(encoding='utf-8')
version = re.search(r'^PROMPT_VERSION\s*=\s*(\d+)\s*$', source, re.MULTILINE)
assert version and int(version.group(1)) >= 14
assert 'TRACE|WRITE_VALUE|springMint|value=label_=Lemon mint' in source

exercise = {
    'topic': 'pointers',
    'hidden_test_file': 'tests/pointer_visualization_fixture.cpp',
}

hidden = '''
std::cerr << "TRACE|CREATE_OBJECT|springMint|type=Plant|value=label_=Spring mint\\n";
std::cerr << "TRACE|CREATE_OBJECT|display|type=GardenDisplay|pointer=focused_\\n";
std::cerr << "TRACE|SET_NULL|display.focused_|pointer cleared\\n";
std::cerr << "TRACE|BIND_POINTER|display.focused_|springMint\\n";
springMint.rename("Lemon mint");
std::cerr << "TRACE|WRITE_VALUE|springMint|value=label_=Lemon mint\\n";
'''

files = {'tests/pointer_visualization_fixture.cpp': hidden}
assert pointer_trace_shape_issues(exercise, files) == []
normalized = normalize_hidden_runtime_artifact(hidden, 'pointers')
assert 'TRACE|WRITE_VALUE|springMint|value=label_=Lemon mint' in normalized

timeline = {
    'timeline': [
        {
            'step': 1,
            'cause': {'type': 'CREATE_OBJECT', 'subject': 'springMint', 'detail': 'type=Plant|value=label_=Spring mint'},
            'active_scopes': [], 'stack_values': [], 'aliases': [],
            'stack': [{'name': 'springMint', 'alive': True, 'fields': {}}], 'heap': [],
        },
        {
            'step': 2,
            'cause': {'type': 'CREATE_OBJECT', 'subject': 'display', 'detail': 'type=GardenDisplay|pointer=focused_'},
            'active_scopes': [], 'stack_values': [], 'aliases': [],
            'stack': [
                {'name': 'springMint', 'alive': True, 'fields': {}},
                {'name': 'display', 'alive': True, 'fields': {'focused_': {'points_to': ''}}},
            ], 'heap': [],
        },
        {
            'step': 3,
            'cause': {'type': 'SET_NULL', 'subject': 'display.focused_', 'detail': 'pointer cleared'},
            'active_scopes': [], 'stack_values': [], 'aliases': [],
            'stack': [
                {'name': 'springMint', 'alive': True, 'fields': {}},
                {'name': 'display', 'alive': True, 'fields': {'focused_': {'points_to': ''}}},
            ], 'heap': [],
        },
        {
            'step': 4,
            'cause': {'type': 'BIND_POINTER', 'subject': 'display.focused_', 'detail': 'springMint'},
            'active_scopes': [], 'stack_values': [], 'aliases': [],
            'stack': [
                {'name': 'springMint', 'alive': True, 'fields': {}},
                {'name': 'display', 'alive': True, 'fields': {'focused_': {'points_to': 'springMint'}}},
            ], 'heap': [],
        },
        {
            'step': 5,
            'cause': {'type': 'WRITE_VALUE', 'subject': 'springMint', 'detail': 'value=label_=Lemon mint'},
            'active_scopes': [], 'stack_values': [], 'aliases': [],
            'stack': [
                {'name': 'springMint', 'alive': True, 'fields': {}},
                {'name': 'display', 'alive': True, 'fields': {'focused_': {'points_to': 'springMint'}}},
            ], 'heap': [],
        },
    ]
}
assert validate_timeline_integrity(timeline) == []

index = (PROJECT_ROOT / 'visualizer/index.html').read_text(encoding='utf-8')
script = (PROJECT_ROOT / 'visualizer/pointer_visualizer.js').read_text(encoding='utf-8')
styles = (PROJECT_ROOT / 'visualizer/styles.css').read_text(encoding='utf-8')
assert re.search(
    r'<script\s+src="pointer_visualizer\.js(?:\?[^"]*)?"></script>',
    index
), (
    "visualizer/index.html must load pointer_visualizer.js; "
    "an optional cache-busting query string is allowed."
)
for required in [
    'Stack pointee created',
    'non-owning stack-to-stack relationship',
    'Pointee value changes',
    'stack-pointer-enhancement',
    'data-stack-object-value',
]:
    assert required in script, required
assert '.object-value' in styles
node = shutil.which('node')
if node:
    result = subprocess.run([node, '--check', str(PROJECT_ROOT / 'visualizer/pointer_visualizer.js')], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
print('Step 30.6 stack-pointee visualization regression test: PASS')
