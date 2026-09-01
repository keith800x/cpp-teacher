#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from exercise_validator import validate_timeline_integrity
CID='ai_move_semantics_20260828_101133_286f4d'
candidate=json.loads((ROOT/'candidates/generated'/f'{CID}.json').read_text())
exercise=candidate['exercise']; files=candidate['files']
assert exercise['difficulty']=='easy'
assert ': load_(other.load_)' in exercise['starter_code']
assert ': load_(std::move(other.load_))' in exercise['reference_solution']
checks=exercise['concept_checks']
assert {c['type'] for c in checks}=={'move_constructor','std_move_initializer'}
sm=next(c for c in checks if c['type']=='std_move_initializer')
assert sm['class']=='FieldKit' and sm['variable']=='load_' and sm['argument']=='other.load_'

obj={'name':'loadingKit','type':'FieldKit','scope':'handoff','alive':True,'lifetime':'alive','fields':{}}
alias_live={'name':'other','target':'loadingKit','scope':'FieldKit','alive':True,'const':False,'type':'FieldKit&&'}
alias_dead={**alias_live,'alive':False}
timeline={'exercise_id':'move-alias-probe','timeline':[
 {'step':1,'cause':{'type':'ENTER_SCOPE','subject':'handoff','detail':''},'active_scopes':['handoff'],'stack':[],'stack_values':[],'aliases':[],'heap':[]},
 {'step':2,'cause':{'type':'CREATE_OBJECT','subject':'loadingKit','detail':'type=FieldKit'},'active_scopes':['handoff'],'stack':[dict(obj)],'stack_values':[],'aliases':[],'heap':[]},
 {'step':3,'cause':{'type':'ENTER_SCOPE','subject':'FieldKit','detail':''},'active_scopes':['handoff','FieldKit'],'stack':[dict(obj)],'stack_values':[],'aliases':[],'heap':[]},
 {'step':4,'cause':{'type':'BIND_ALIAS','subject':'other','detail':'target=loadingKit'},'active_scopes':['handoff','FieldKit'],'stack':[dict(obj)],'stack_values':[],'aliases':[dict(alias_live)],'heap':[]},
 {'step':5,'cause':{'type':'EXIT_SCOPE','subject':'FieldKit','detail':''},'active_scopes':['handoff'],'stack':[dict(obj)],'stack_values':[],'aliases':[dict(alias_dead)],'heap':[]},
 {'step':6,'cause':{'type':'DESTROY_BEGIN','subject':'loadingKit','detail':''},'active_scopes':['handoff'],'stack':[{**obj,'lifetime':'destroying'}],'stack_values':[],'aliases':[dict(alias_dead)],'heap':[]},
 {'step':7,'cause':{'type':'DESTROY_END','subject':'loadingKit','detail':''},'active_scopes':['handoff'],'stack':[{**obj,'alive':False,'lifetime':'destroyed'}],'stack_values':[],'aliases':[dict(alias_dead)],'heap':[]},
 {'step':8,'cause':{'type':'EXIT_SCOPE','subject':'handoff','detail':''},'active_scopes':[],'stack':[{**obj,'alive':False,'lifetime':'destroyed'}],'stack_values':[],'aliases':[dict(alias_dead)],'heap':[]},
]}
issues=validate_timeline_integrity(timeline)
assert not issues, issues
bad=json.loads(json.dumps(timeline)); bad['timeline'][3]['cause']['detail']='target=missingKit'; bad['timeline'][3]['aliases'][0]['target']='missingKit'
bad_issues=validate_timeline_integrity(bad)
assert any('unknown stack value or stack object' in x or 'no stack value or stack object' in x for x in bad_issues),bad_issues

clang=shutil.which('clang++')
if clang:
    with tempfile.TemporaryDirectory(prefix='cpp_teacher_move_ast_') as td:
        temp=Path(td); src=temp/'reference.cpp'
        src.write_text(files[exercise['analysis_support_file']]+'\n'+exercise['reference_solution'])
        r=subprocess.run([clang,'-std=c++20','-fsyntax-only','-Xclang','-ast-dump=json','-Xclang','-ast-dump-filter','-Xclang','FieldKit',str(src)],text=True,capture_output=True)
        assert r.returncode==0,r.stderr
        start=r.stdout.find('{'); assert start>=0; ast=json.loads(r.stdout[start:])
        def walk(n):
            if isinstance(n,dict):
                yield n
                for c in n.get('inner',[]): yield from walk(c)
            elif isinstance(n,list):
                for c in n: yield from walk(c)
        inits=[n for n in walk(ast) if n.get('kind')=='CXXCtorInitializer' and isinstance(n.get('anyInit'),dict) and n['anyInit'].get('name')=='load_']
        assert inits
        text=src.read_text(); found=False
        for init in inits:
            inner=init.get('inner',[])
            if not inner: continue
            rng=inner[0].get('range',{}); b=rng.get('begin',{}).get('offset'); e_info=rng.get('end',{}); e=e_info.get('offset'); tl=e_info.get('tokLen',1)
            if isinstance(b,int) and isinstance(e,int):
                frag=text[b:e+tl]
                if 'std::move' in frag and 'other.load_' in frag: found=True; break
        assert found

compiler=shutil.which('g++') or shutil.which('clang++')
if compiler:
    def run_case(name,code):
        with tempfile.TemporaryDirectory(prefix='cpp_teacher_'+name+'_') as td:
            temp=Path(td); src=temp/(name+'.cpp'); exe=temp/name
            src.write_text(files[exercise['support_file']]+'\n'+code+'\n'+files[exercise['hidden_test_file']])
            b=subprocess.run([compiler,'-std=c++20',str(src),'-o',str(exe)],text=True,capture_output=True)
            assert b.returncode==0,b.stderr
            return subprocess.run([str(exe)],text=True,capture_output=True)
    ref=run_case('move_reference',exercise['reference_solution']); starter=run_case('move_starter',exercise['starter_code'])
    assert ref.returncode==0,ref.stderr
    assert starter.returncode!=0
print('Step 30.8.0 Move Semantics Easy runtime-contract regression: PASS')
