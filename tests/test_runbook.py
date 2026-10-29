"""Actual contract with mocked GenLayer boundary: no real consensus claimed."""
import importlib.util
import itertools
import json
import sys
import types
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OWNER='0x'+'1'*40
OTHER='0x'+'2'*40
STRANGER='0x'+'3'*40
class Return:
    def __init__(self,value):self.calldata=value
class API:
    write=staticmethod(lambda f:f)
    view=staticmethod(lambda f:f)
gl=types.SimpleNamespace(Contract=object,public=API(),message=types.SimpleNamespace(sender_address=OWNER),
    vm=types.SimpleNamespace(UserError=ValueError,Return=Return),nondet=types.SimpleNamespace())
sys.modules['genlayer']=types.SimpleNamespace(gl=gl,TreeMap=dict)
spec=importlib.util.spec_from_file_location('runbook',ROOT/'contracts/runbook_latch.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
INPUT=json.loads((ROOT/'examples/release.json').read_text())
PLAN=c.parse_plan(json.dumps(INPUT))

def findings(plan=PLAN, required=None, unclear=None):
    if required is None:required={('assemble','publish'),('review','publish')}
    unclear=unclear or set()
    return {'relations':[{'before':a,'after':b,'kind':'UNCLEAR' if (a,b) in unclear else 'REQUIRED' if (a,b) in required else 'NO_DIRECT',
      'rule_indices':[0],'reason':'The procedure explicitly defines the stated prerequisite relation.'}
      for a,b in c.ordered_pairs(plan['steps'])]}

class RunbookTests(unittest.TestCase):
    def setUp(self):
        gl.message.sender_address=OWNER
        self.contract=c.RunbookLatch();self.answer=findings();self.independent=None;self.audit=True;self.prompts=[]
        def llm(prompt,**kw):
            self.prompts.append(prompt)
            if prompt.startswith('Audit '):return {'valid':self.audit}
            return self.independent if self.independent is not None and len(self.prompts)>1 else self.answer
        gl.nondet.exec_prompt=llm
        def run(leader,validator):
            candidate=leader()
            if not validator(Return(candidate)):raise ValueError('CONSENSUS_REJECTED')
            return candidate
        gl.vm.run_nondet_unsafe=run
    def open(self):return json.loads(self.contract.open_run('release',json.dumps(INPUT)))
    def compile(self):return json.loads(self.contract.compile_run(OWNER,'release'))
    def read(self):return json.loads(self.contract.get_run(OWNER,'release'))
    def ack(self,step,digest=None):
        return json.loads(self.contract.acknowledge(OWNER,'release',step,digest or self.read()['graph_digest'],'Synthetic completion acknowledgement.'))
    def test_parallel_join_lifecycle(self):
        self.open();self.compile();self.assertEqual(self.read()['available'],['assemble','review'])
        self.ack('assemble');gl.message.sender_address=OTHER
        with self.assertRaisesRegex(ValueError,'PREREQUISITES_PENDING'):self.ack('publish')
        self.ack('review');self.assertEqual(self.read()['available'],['publish'])
        self.ack('publish');self.assertEqual(self.read()['status'],'COMPLETE');self.assertEqual(self.read()['available'],[])
    def test_no_owner_override(self):
        self.open();self.compile()
        with self.assertRaisesRegex(ValueError,'NOT_EXECUTOR'):self.ack('review')
    def test_reverse_parallel_order(self):
        self.open();self.compile();gl.message.sender_address=OTHER;self.ack('review')
        gl.message.sender_address=OWNER;self.ack('assemble');gl.message.sender_address=OTHER
        self.assertEqual(self.ack('publish')['status'],'COMPLETE')
    def test_cycle_blocks_all(self):
        self.open();self.answer=findings(required={('assemble','review'),('review','assemble')})
        self.assertEqual(self.compile()['status'],'CYCLE');self.assertEqual(self.read()['available'],[])
        with self.assertRaisesRegex(ValueError,'RUN_NOT_ACTIVE'):self.ack('assemble')
    def test_unclear_blocks_all(self):
        self.open();self.answer=findings(unclear={('assemble','review')})
        self.assertEqual(self.compile()['status'],'REVIEW')
        with self.assertRaisesRegex(ValueError,'RUN_NOT_ACTIVE'):self.ack('assemble')
    def test_independent_mismatch_atomic(self):
        self.open();self.independent=findings(required=set())
        with self.assertRaisesRegex(ValueError,'CONSENSUS_REJECTED'):self.compile()
        self.assertEqual(self.read()['status'],'OPEN');self.assertEqual(self.read()['findings'],[])
    def test_quote_rejection(self):
        self.open();self.answer['relations'][0]['quote']='Unquoted fabricated instruction.'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_QUOTE'):self.compile()
    def test_rule_reference_bounds(self):
        for indices in [[],[False],[-1],[1],[0,0],['0']]:
            raw=findings();raw['relations'][0]['rule_indices']=indices
            with self.assertRaisesRegex(ValueError,'INVALID_RULE_REFERENCE'):c.read_findings(raw,PLAN)
    def test_audit_requires_literal_true(self):
        self.open();self.audit='true'
        with self.assertRaisesRegex(ValueError,'CONSENSUS_REJECTED'):self.compile()
    def test_digest_binding(self):
        self.open();self.compile()
        with self.assertRaisesRegex(ValueError,'GRAPH_DIGEST_MISMATCH'):self.ack('assemble','0'*64)
    def test_repeat_ack(self):
        self.open();self.compile();self.ack('assemble')
        with self.assertRaisesRegex(ValueError,'ALREADY_ACKNOWLEDGED'):self.ack('assemble')
    def test_immutable_ids_and_graph(self):
        self.open()
        with self.assertRaisesRegex(ValueError,'RUN_EXISTS'):self.open()
        self.compile()
        with self.assertRaisesRegex(ValueError,'RUN_COMPILED'):self.compile()
    def test_namespaces(self):
        self.open();gl.message.sender_address=OTHER;self.open();self.assertEqual(len(self.contract.runs),2)
    def test_stranger_compile(self):
        self.open();gl.message.sender_address=STRANGER
        with self.assertRaisesRegex(ValueError,'NOT_PARTICIPANT'):self.compile()
    def test_executor_can_compile(self):
        self.open();gl.message.sender_address=OTHER;self.assertEqual(self.compile()['status'],'ACTIVE')
    def test_matrix_complete_and_ordered(self):
        for raw in [ {'relations':findings()['relations'][:-1]}, {'relations':list(reversed(findings()['relations']))} ]:
            with self.assertRaises(ValueError):c.read_findings(raw,PLAN)
    def test_input_limits_duplicates(self):
        for plan in [dict(INPUT,steps=[]),dict(INPUT,steps=[INPUT['steps'][0]]*2),dict(INPUT,procedure='tiny')]:
            with self.assertRaises(ValueError):c.parse_plan(json.dumps(plan))
    def test_no_edges_all_parallel(self):
        self.open();self.answer=findings(required=set());self.compile()
        self.assertEqual(self.read()['available'],['assemble','review','publish'])
    def test_chain_transitive_enforcement(self):
        self.open();self.answer=findings(required={('assemble','review'),('review','publish')});self.compile()
        self.assertEqual(self.read()['available'],['assemble'])
        self.ack('assemble');gl.message.sender_address=OTHER
        with self.assertRaisesRegex(ValueError,'PREREQUISITES_PENDING'):self.ack('publish')
        self.ack('review');self.ack('publish');self.assertEqual(self.read()['status'],'COMPLETE')
    def test_note_failure_does_not_mutate(self):
        self.open();self.compile()
        with self.assertRaisesRegex(ValueError,'INVALID_TEXT'):self.contract.acknowledge(OWNER,'release','assemble',self.read()['graph_digest'],'x')
        self.assertEqual(self.read()['journal'],[])
    def test_all_binary_graphs_against_permutation_oracle(self):
        pairs=c.ordered_pairs(PLAN['steps']);ids=[s['id'] for s in PLAN['steps']]
        for bits in itertools.product([False,True],repeat=len(pairs)):
            required={pair for pair,bit in zip(pairs,bits) if bit}
            graph=c.compile_graph(PLAN['steps'],findings(required=required)['relations'])
            valid_orders=[order for order in itertools.permutations(ids) if all(order.index(a)<order.index(b) for a,b in required)]
            self.assertEqual(graph['status']=='ACTIVE',bool(valid_orders))
            if valid_orders:
                flat=[n for layer in graph['layers'] for n in layer]
                self.assertTrue(all(flat.index(a)<flat.index(b) for a,b in required))
                for mask in range(8):
                    done={ids[i]:{} for i in range(3) if mask&(1<<i)}
                    r={'status':'ACTIVE','plan':PLAN,'graph':graph,'acknowledgements':done}
                    expected=[n for n in ids if n not in done and {a for a,b in required if b==n}.issubset(done)]
                    self.assertEqual(c.available(r),expected)

if __name__=='__main__':unittest.main()
