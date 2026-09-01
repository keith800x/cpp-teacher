#!/usr/bin/env python3
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import exercise_validator as validator

candidate = json.loads(
    (ROOT / "candidates/generated/ai_raii_scope_20260825_080542_06bcf3.json")
    .read_text(encoding="utf-8")
)
exercise = candidate["exercise"]
files = candidate["files"]

assert validator.raii_exact_sequence_grading_issues(exercise, files) == []

hidden = files[exercise["hidden_test_file"]]
assert "harborAuditMatches(expected)" not in hidden
assert "before(" in hidden

bad_files = dict(files)
bad_files[exercise["hidden_test_file"]] = r"""
#include <string>
#include <vector>
int main() {
    const std::vector<std::string> expected = {
        "create:x",
        "use:x",
        "destroy:x"
    };
    if (!harborAuditMatches(expected)) {
        return 2;
    }
    return 0;
}
"""
bad_files[exercise["support_file"]] = r"""
#include <string>
#include <vector>
inline std::vector<std::string>& harborAudit() {
    static std::vector<std::string> events;
    return events;
}
inline bool harborAuditMatches(
    const std::vector<std::string>& expected) {
    return harborAudit() == expected;
}
"""
bad_issues = validator.raii_exact_sequence_grading_issues(
    exercise,
    bad_files,
)
assert bad_issues
assert any("helper" in issue.lower() for issue in bad_issues)

server = (ROOT / "dev_server.py").read_text(encoding="utf-8")
assert server.count("visualization_timeline_for_client(") >= 6

grade_snippet = """\"timeline\":
                visualization_timeline_for_client(
                    exercise_id,
                    grader_result[
                        \"timeline\"
                    ],
                ),"""
assert grade_snippet in server

solution_tail = server[server.index("archive_solution_timeline("):]
solution_snippet = """\"timeline\":
                visualization_timeline_for_client(
                    exercise_id,
                    timeline,
                ),"""
assert solution_snippet in solution_tail

raii = (ROOT / "visualizer/raii_visualizer.js").read_text(encoding="utf-8")
index = (ROOT / "visualizer/index.html").read_text(encoding="utf-8")
assert "function displayedTimelineMatches(" in raii
assert '"Visualization refresh required"' in raii
assert "raii_visualizer.js?v=30.7.6" in index

node = shutil.which("node")
if node:
    result = subprocess.run(
        [node, "--check", str(ROOT / "visualizer/raii_visualizer.js")],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr

print("Step 30.7.3 RAII legacy-verification regression: PASS")
