// Explicit development writes on Stable Studionet; every existing intent/hash is resumed.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient,abi} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import {generatePrivateKey,privateKeyToAccount} from 'viem/accounts';
const root=path.resolve(import.meta.dirname,'..');
const location=process.env.RUNBOOKLATCH_STATE||path.join(os.homedir(),'.runbooklatch-studionet-v1.json');
const json=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v,2);
let session;
if(fs.existsSync(location))session=JSON.parse(fs.readFileSync(location));
else{
 if(process.env.RUNBOOKLATCH_NEW!=='1')throw Error('Set RUNBOOKLATCH_NEW=1 once for a new isolated zero-value test.');
 session={keys:[generatePrivateKey(),generatePrivateKey()],transactions:{}};
 fs.writeFileSync(location,json(session),{mode:0o600});
}
const persist=()=>fs.writeFileSync(location,json(session),{mode:0o600});
const accounts=session.keys.map(privateKeyToAccount);
const clients=accounts.map(account=>createClient({chain:studionet,account}));
const owner=accounts[0].address,other=accounts[1].address;
const client=clients[0];
assert.equal(Number(await client.getChainId()),61999);
const source=fs.readFileSync(path.join(root,'contracts/runbook_latch.py'),'utf8');
const sourceSha256=crypto.createHash('sha256').update(source).digest('hex');
if(session.sourceSha256)assert.equal(session.sourceSha256,sourceSha256,'Do not resume changed source');
session.sourceSha256=sourceSha256;persist();
const normalize=r=>{
 r.resultName??=r.result_name;
 r.txExecutionResultName??=r.consensus_data?.leader_receipt?.find(x=>x.mode==='leader')?.execution_result;
 return r;
};
async function transact(label,signer,method,args,expected='SUCCESS'){
 let tx=session.transactions[label];
 if(!tx){
  tx=session.transactions[label]={signer:accounts[signer].address,method,args,intent:true};persist();
  // A send that throws leaves an unresolved intent: never automatically resend it.
  tx.hash=method==='deploy'?await clients[signer].deployContract({code:source,args:[],leaderOnly:false}):
   await clients[signer].writeContract({address:session.address,functionName:method,args,value:0n,leaderOnly:false});
  persist();console.log(label,'submitted',tx.hash);
 }
 assert.equal(tx.signer,accounts[signer].address);assert.equal(tx.method,method);assert.deepEqual(tx.args,args);
 if(!tx.hash)throw Error('Unresolved send intent '+label);
 for(let i=0;i<180;i++){
  if(tx.receipt?.statusName==='FINALIZED')break;
  tx.receipt=normalize(await client.getTransaction({hash:tx.hash}));persist();
  if(['UNDETERMINED','CANCELED'].includes(tx.receipt.statusName))throw Error(label+' terminal failure: inspect existing hash');
  if(tx.receipt.statusName!=='FINALIZED')await new Promise(r=>setTimeout(r,2000));
 }
 const r=normalize(tx.receipt);persist();
 assert.equal(r.statusName,'FINALIZED','Resume pending hash');assert.equal(r.resultName,'MAJORITY_AGREE');
 assert.equal(r.txExecutionResultName,expected);assert.equal(r.from_address.toLowerCase(),tx.signer.toLowerCase());
 assert.equal(r.leader_only,false);
 if(method==='deploy'){
  session.address=r.to_address;persist();assert.equal(Buffer.from(r.data.contract_code,'base64').toString(),source);
 }else{
  assert.equal(r.to_address.toLowerCase(),session.address.toLowerCase());
  const decoded=abi.calldata.decode(Buffer.from(r.data.calldata.base64,'base64'));
  assert.equal(decoded.get('method'),method);assert.deepEqual(decoded.get('args'),args);
 }
 console.log(label,r.statusName,r.resultName,r.txExecutionResultName);
 return r;
}
await transact('deploy',0,'deploy',[]);
assert.equal(await client.getContractCode(session.address),source);
const plan=JSON.parse(fs.readFileSync(path.join(root,'examples/release.json')));
plan.steps[0].executor=owner;plan.steps[1].executor=other;plan.steps[2].executor=other;
session.plan=plan;persist();
const read=async()=>JSON.parse(await client.readContract({address:session.address,functionName:'get_run',args:[owner,'release-demo'],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}));
await transact('open',0,'open_run',['release-demo',JSON.stringify(plan)]);
await transact('compile',0,'compile_run',[owner,'release-demo']);
let record=await read();
assert.deepEqual(record.graph.edges,[['assemble','publish'],['review','publish']]);
assert.equal(record.graph.status,'ACTIVE');
const digest=record.graph_digest;
await transact('assemble',0,'acknowledge',[owner,'release-demo','assemble',digest,'Synthetic test: release bundle assembly acknowledged.']);
if(!session.transactions.review){
 record=await read();assert.equal(record.status,'ACTIVE');assert.deepEqual(record.available,['review']);
}
const rejected=await transact('reject_early_publish',1,'acknowledge',[owner,'release-demo','publish',digest,'Synthetic test: attempt distribution before notes are checked.'],'ERROR');
assert.ok(JSON.stringify(rejected.consensus_data.leader_receipt.find(x=>x.mode==='leader').result).includes('PREREQUISITES_PENDING'));
if(!session.transactions.review){record=await read();assert.equal(record.journal.length,1);assert.deepEqual(record.available,['review']);}
await transact('review',1,'acknowledge',[owner,'release-demo','review',digest,'Synthetic test: release-note review acknowledged.']);
await transact('publish',1,'acknowledge',[owner,'release-demo','publish',digest,'Synthetic test: public archive distribution acknowledged.']);
record=await read();assert.equal(record.status,'COMPLETE');assert.deepEqual(record.available,[]);
assert.deepEqual(record.journal.map(x=>x.step),['assemble','review','publish']);
function receiptProjection(r){
 return {hash:r.hash,statusName:r.statusName,resultName:r.resultName,txExecutionResultName:r.txExecutionResultName,
  from_address:r.from_address,to_address:r.to_address,leader_only:r.leader_only,
  data:{...r.data,calldata:{base64:r.data?.calldata?.base64}},
  consensus_data:{votes:r.consensus_data?.votes,leader_receipt:r.consensus_data?.leader_receipt?.map(l=>({mode:l.mode,execution_result:l.execution_result,
    result:{status:l.result?.status,payload:typeof l.result?.payload==='object'?{readable:l.result.payload?.readable}:l.result?.payload}}))}};
}
const evidence={network:{chainId:61999,rpc:'https://studio.genlayer.com/api'},address:session.address,owner,other,sourceSha256,plan,
 note:'Synthetic public release workflow; two test wallets controlled by one operator. Acknowledgements do not prove external work. Projected public receipt fields; node configuration, timing logs and redundant arrays omitted.',
 transactions:Object.fromEntries(Object.entries(session.transactions).map(([name,tx])=>[name,{hash:tx.hash,signer:tx.signer,method:tx.method,args:tx.args,receipt:receiptProjection(tx.receipt)}])),record};
fs.writeFileSync(path.join(root,'evidence/studionet.json'),json(evidence)+'\n');
console.log('VERIFIED',session.address,record.status);
