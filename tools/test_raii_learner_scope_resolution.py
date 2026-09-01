#!/usr/bin/env python3
from __future__ import annotations
import ast
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
server_path=ROOT/'dev_server.py'
source=server_path.read_text(encoding='utf-8')
tree=ast.parse(source, filename=str(server_path))
functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
for name in [
    'raii_target_function_from_code',
    'raii_internal_lifecycle_scope',
    'raii_cause_for_client',
    'raii_object_for_client',
    'visualization_timeline_for_client',
]: assert name in functions, name

# Exercise-code resolution works for free functions and class methods.
module=ast.Module(body=[functions['raii_target_function_from_code']],type_ignores=[]); ast.fix_missing_locations(module)
ns={'re':__import__('re')}; exec(compile(module,str(server_path),'exec'),ns)
assert ns['raii_target_function_from_code']('void completeShipment()\n{\n}\n')=='completeShipment'
assert ns['raii_target_function_from_code']('class X { public: void prepareEveningExhibit() { } };')=='prepareEveningExhibit'

wanted=['raii_internal_lifecycle_scope','raii_cause_for_client','raii_object_for_client','visualization_timeline_for_client']
module=ast.Module(body=[functions[n] for n in wanted],type_ignores=[]); ast.fix_missing_locations(module)
ns={
    'exercise_topic_for_visualization':lambda exercise_id:'raii_scope',
    'raii_learner_operation_for_visualization':lambda exercise_id:'completeShipment',
}
exec(compile(module,str(server_path),'exec'),ns)
raw={'timeline':[
    {'step':1,'active_scopes':['ShipmentAsset::ShipmentAsset'],'cause':{'type':'CREATE_OBJECT','subject':'gelPack','detail':'type=ColdPack|pointer=payload_'},'stack':[{'name':'gelPack','scope':'ShipmentAsset::ShipmentAsset','fields':{'payload_':{'kind':'pointer','points_to':None}}}],'heap':[]},
    {'step':2,'active_scopes':['chillCargo'],'cause':{'type':'ENTER_SCOPE','subject':'chillCargo','detail':''},'stack':[{'name':'gelPack','scope':'ShipmentAsset::ShipmentAsset','fields':{'payload_':{'kind':'pointer','points_to':'resource#2'}}}],'heap':[{'id':'resource#2','alive':True}]},
    {'step':3,'active_scopes':[],'cause':{'type':'EXIT_SCOPE','subject':'chillCargo','detail':''},'stack':[],'heap':[]},
]}
clean=ns['visualization_timeline_for_client']('medium-probe',raw)
assert clean['raii_learner_operation']=='completeShipment'
assert [f['cause']['subject'] for f in clean['timeline']]==['gelPack','chillCargo','chillCargo']
assert clean['timeline'][0]['stack'][0]['scope']=='completeShipment'
assert clean['timeline'][1]['stack'][0]['scope']=='completeShipment'
# No completeShipment frame is invented when runtime never emitted one.
assert all(f['cause']['subject']!='completeShipment' for f in clean['timeline'])

js=(ROOT/'visualizer/raii_visualizer.js').read_text(encoding='utf-8')
assert 'documentData?.raii_learner_operation' in js
# Old first-ENTER_SCOPE inference must be gone.
assert 'for (const frame of list)' not in js[js.index('function learnerOperationName('):js.index('function teachRaiiFrame(')]
index=(ROOT/'visualizer/index.html').read_text(encoding='utf-8')
assert 'raii_visualizer.js?v=30.7.6' in index
node=shutil.which('node')
if node:
    r=subprocess.run([node,'--check',str(ROOT/'visualizer/raii_visualizer.js')],text=True,capture_output=True)
    assert r.returncode==0,r.stderr
print('Step 30.7.6 RAII learner-scope resolution regression: PASS')
