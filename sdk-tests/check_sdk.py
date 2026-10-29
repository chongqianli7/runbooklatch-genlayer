"""Pinned SDK and storage smoke check, with explicit model mocks; not network consensus."""
import json
from pathlib import Path
from gltest.direct import VMContext, deploy_contract
root=Path(__file__).resolve().parents[1]
plan=json.loads((root/'examples/release.json').read_text())
owner=plan['steps'][0]['executor'];other=plan['steps'][1]['executor']
relations=[]
for a in plan['steps']:
    for b in plan['steps']:
        if a==b:continue
        relations.append({'before':a['id'],'after':b['id'],'kind':'REQUIRED' if b['id']=='publish' else 'NO_DIRECT',
          'rule_indices':[0],'reason':'The procedure explicitly requires both preparations before distribution.'})
vm=VMContext();vm.sender=owner
vm.mock_llm('^Interpret',json.dumps({'relations':relations}));vm.mock_llm('^Audit',json.dumps({'valid':True}))
with vm.activate():
    run=deploy_contract(root/'contracts/runbook_latch.py',vm,sdk_version='v0.3.0-rc7')
    run.open_run('sdk',json.dumps(plan));r=json.loads(run.compile_run(owner,'sdk'))
    assert r['graph']['layers']==[['assemble','review'],['publish']]
    assert vm.run_validator() is True
    vm.clear_mocks();changed=json.loads(json.dumps(relations));changed[0]['kind']='UNCLEAR'
    vm.mock_llm('^Interpret',json.dumps({'relations':changed}))
    assert vm.run_validator() is False
    run.acknowledge(owner,'sdk','assemble',r['graph_digest'],'Synthetic assembly acknowledged.')
    with vm.prank(other):
        try:run.acknowledge(owner,'sdk','publish',r['graph_digest'],'Synthetic early distribution.')
        except Exception as exc:assert 'PREREQUISITES_PENDING' in str(exc)
        else:raise AssertionError('join gate bypassed')
        run.acknowledge(owner,'sdk','review',r['graph_digest'],'Synthetic review acknowledged.')
        run.acknowledge(owner,'sdk','publish',r['graph_digest'],'Synthetic distribution acknowledged.')
    final=json.loads(run.get_run(owner,'sdk'))
    assert final['status']=='COMPLETE' and final['available']==[]
    assert [x['ordinal'] for x in final['journal']]==[1,2,3]
print('PASS: SDK storage/calldata, independent validator acceptance/rejection, conjunctive gate and completion (mocked LLM).')
