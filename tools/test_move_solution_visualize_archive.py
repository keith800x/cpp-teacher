#!/usr/bin/env python3
from __future__ import annotations
import ast
from http import HTTPStatus
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]
server_path=ROOT/'dev_server.py'
server=server_path.read_text(encoding='utf-8')
start=server.index('    def handle_solution_visualize(')
end=server.index('\n\ndef main():',start)
h=server[start:end]
assert h.index('read_candidate_reference_timeline(') < h.index('run_grader(')
for required in [
    'authoring_candidate_id_is_safe(',
    'authoring_candidate_paths(',
    'read_candidate_reference_timeline(',
    'No current validated reference ',
    'visualization_timeline_for_client(',
]: assert required in h, required

# Extract handler into a probe class.
tree=ast.parse(server,filename=str(server_path))
handler_node=None
for node in tree.body:
    if isinstance(node,ast.ClassDef):
        for child in node.body:
            if isinstance(child,ast.FunctionDef) and child.name=='handle_solution_visualize':
                handler_node=child; break
        if handler_node: break
assert handler_node is not None
probe_class=ast.ClassDef(name='ProbeHandler',bases=[],keywords=[],body=[handler_node],decorator_list=[])
module=ast.Module(body=[probe_class],type_ignores=[]); ast.fix_missing_locations(module)
with tempfile.TemporaryDirectory(prefix='cpp_teacher_3084_') as td:
    temp=Path(td); generated_id='ai_move_semantics_probe'; normal_id='move_runtime_trace_001'
    generated_candidate=temp/f'{generated_id}.json'; generated_candidate.write_text('{}\n')
    archive14={'timeline':[{'step':i} for i in range(1,15)]}
    calls=[]
    namespace={
        'HTTPStatus':HTTPStatus,
        'authoring_candidate_id_is_safe':lambda eid:eid.startswith('ai_'),
        'authoring_candidate_paths':lambda eid:(generated_candidate,temp/f'{eid}.validation.json'),
        'read_candidate_reference_timeline':lambda eid:(calls.append(('candidate',eid)) or archive14),
        'visualization_timeline_for_client':lambda eid,t:t,
        'exercise_map':lambda:{generated_id:{'id':generated_id},normal_id:{'id':normal_id}},
        'solution_is_available':lambda eid:True,
        'solution_is_revealed':lambda eid:True,
        'read_exercise_document':lambda item:{'reference_solution':'int main(){}'},
        'validate_exercise_file':lambda item:'exercise.json',
        'run_grader':lambda ef,src:(calls.append(('grader',ef)) or {'grade':{'passed':True},'timeline':{'timeline':[{'step':i} for i in range(1,12)]}}),
        'archive_solution_timeline':lambda eid,t:calls.append(('archive_solution',eid)),
        'subprocess':__import__('subprocess'),
    }
    exec(compile(module,str(server_path),'exec'),namespace)
    ProbeHandler=namespace['ProbeHandler']
    class Probe(ProbeHandler):
        def __init__(self): self.responses=[]
        def send_json(self,payload,status=HTTPStatus.OK): self.responses.append((status,payload))
    p=Probe(); p.handle_solution_visualize(generated_id)
    assert len(p.responses)==1
    status,payload=p.responses[0]; assert status==HTTPStatus.OK
    assert len(payload['timeline']['timeline'])==14
    assert calls==[('candidate',generated_id)],calls
    calls.clear(); p=Probe(); p.handle_solution_visualize(normal_id)
    status,payload=p.responses[0]; assert status==HTTPStatus.OK
    assert len(payload['timeline']['timeline'])==11
    assert calls[0][0]=='grader',calls
    assert any(c[0]=='archive_solution' for c in calls),calls
    # Missing candidate archive must not fall through to old grader path.
    calls.clear()
    namespace['read_candidate_reference_timeline']=lambda eid:(calls.append(('candidate',eid)) or None)
    # Function globals resolve namespace dynamically, no recompile needed.
    p=Probe(); p.handle_solution_visualize(generated_id)
    status,payload=p.responses[0]; assert status==HTTPStatus.NOT_FOUND
    assert 'Revalidate' in payload['error']
    assert not any(c[0]=='grader' for c in calls),calls
print('Step 30.8.4 generated solution-visualize archive regression: PASS')
