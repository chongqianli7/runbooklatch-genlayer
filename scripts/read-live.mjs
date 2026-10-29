// Read-only verification: no account creation, signing or write calls.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient,abi} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
const root=path.resolve(import.meta.dirname,'..');
const evidence=JSON.parse(fs.readFileSync(path.join(root,'evidence/studionet.json')));
const client=createClient({chain:studionet});
assert.equal(Number(await client.getChainId()),61999);
const source=fs.readFileSync(path.join(root,'contracts/runbook_latch.py'),'utf8');
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),evidence.sourceSha256);
assert.equal(await client.getContractCode(evidence.address),source);
const actual=JSON.parse(await client.readContract({address:evidence.address,functionName:'get_run',args:[evidence.owner,'release-demo'],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}));
assert.deepEqual(actual,evidence.record);assert.equal(actual.status,'COMPLETE');
assert.deepEqual(actual.graph.edges,[['assemble','publish'],['review','publish']]);
assert.deepEqual(actual.journal.map(x=>x.step),['assemble','review','publish']);
for(const [name,tx] of Object.entries(evidence.transactions)){
 const r=await client.getTransaction({hash:tx.hash});
 assert.equal(r.statusName,'FINALIZED');assert.equal(r.resultName||r.result_name,'MAJORITY_AGREE');
 assert.equal(r.leader_only,false);assert.equal(r.from_address.toLowerCase(),tx.signer.toLowerCase());
 assert.equal(r.to_address.toLowerCase(),evidence.address.toLowerCase());
 const leader=r.consensus_data?.leader_receipt?.find(x=>x.mode==='leader');
 assert.equal(r.txExecutionResultName||leader?.execution_result,name==='reject_early_publish'?'ERROR':'SUCCESS');
 if(tx.method==='deploy')assert.equal(Buffer.from(r.data.contract_code,'base64').toString(),source);
 else{
  const decoded=abi.calldata.decode(Buffer.from(r.data.calldata.base64,'base64'));
  assert.equal(decoded.get('method'),tx.method);assert.deepEqual(decoded.get('args'),tx.args);
 }
 if(name==='reject_early_publish')assert.ok(JSON.stringify(leader.result).includes('PREREQUISITES_PENDING'));
 console.log(name,tx.hash,'FINALIZED');
}
console.log('VERIFIED: deployed source, receipt binding, full consensus and finalized COMPLETE record.');
