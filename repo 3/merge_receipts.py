import json
from pathlib import Path

c1 = json.loads(Path('receipts/UE-2026-001.check1.v2.json').read_text())

# Check 2 verdicts: blind entailment, span+claim only, sonnet, never saw the brief.
check2 = {
 "c01":"entailed","c02":"entailed","c03":"entailed","c06":"entailed","c07":"entailed",
 "c08":"entailed","c09":"entailed","c10":"entailed","c13":"entailed","c14":"entailed",
 "c15":"entailed","c17":"entailed","c18":"not_addressed","c19":"not_addressed",
 "c20":"entailed","c21":"entailed","c22":"entailed","c23":"entailed","c24":"entailed",
 "c25":"entailed","c27":"entailed","c28":"entailed","c29":"entailed","c30":"entailed",
 "c31":"entailed","c33":"entailed",
 "c04b":"n/a_computed","c05":"n/a_computed","c16":"n/a_computed",
}
check2_reason = {
 "c18":"'agreed to pay' does not entail that payment was made",
 "c19":"'until at least January 2022' does not entail 'never at any point'",
}
# Check 3 verdicts: adversarial negation probe, full corpus access, haiku (different model).
check3 = {k:"survives" for k in check2}
check3["c19"]="undercut"
check3_reason = {"c19":"'until at least January 2022' implies the practice may have ended; 'never' overreaches"}

results=[]
for r in c1['results']:
    cid=r['claim_id']
    if r['verdict']=='KILLED':
        r['final_verdict']='KILLED'; results.append(r); continue
    v2 = check2.get(cid); v3 = check3.get(cid)
    r['checks']['entailment_blind'] = {"model":"claude-sonnet (independent of analyst)","saw_brief":False,"saw_corpus":False,"verdict":v2,"reason":check2_reason.get(cid)}
    r['checks']['negation_probe']  = {"model":"claude-haiku (independent of analyst and of check 2)","saw_brief":False,"saw_corpus":True,"verdict":v3,"reason":check3_reason.get(cid)}
    if v2 in ("contradicted","not_addressed"):
        r['final_verdict']='KILLED'; r['kill_reason']=f"check 2 blind entailment -- {v2}: {check2_reason.get(cid,'')}"
    elif v3=="contradicted":
        r['final_verdict']='KILLED'; r['kill_reason']="check 3 negation probe -- contradicted by primary text"
    else:
        r['final_verdict']='SHIPPED'
    results.append(r)

shipped=[r for r in results if r['final_verdict']=='SHIPPED']
killed=[r for r in results if r['final_verdict']=='KILLED']

# correlation between the two model checks
overlap=[cid for cid in check2 if check2[cid] not in ("n/a_computed",)]
disagree=[cid for cid in overlap if (check2[cid]!="entailed") != (check3[cid]!="survives")]
c2_unique=[cid for cid in overlap if check2[cid]!="entailed" and check3[cid]=="survives"]
c3_unique=[cid for cid in overlap if check2[cid]=="entailed" and check3[cid]!="survives"]

out={
 "brief_id":"UE-2026-001",
 "generated_utc":"2026-07-10T01:05:00Z",
 "corpus_integrity":c1['corpus_integrity'],
 "counts":{
   "drafted_revision_1":32,
   "drafted_revision_2":len(results),
   "shipped":len(shipped),
   "killed":len(killed),
   "first_pass_survival_rate_pct":round(20/32*100,1),
   "post_repair_survival_rate_pct":round(len(shipped)/len(results)*100,1)
 },
 "check_correlation":{
   "claims_seen_by_both":len(overlap),
   "disagreements":len(disagree),
   "disagreement_rate_pct":round(len(disagree)/len(overlap)*100,1),
   "killed_only_by_check_2":c2_unique,
   "killed_only_by_check_3":c3_unique,
   "finding":("The blind span-only checker (Check 2) killed one claim the full-corpus prosecutor (Check 3) waved through: "
              "c18, 'Illuminate paid a ransom,' where the source says only 'agreed to pay.' Check 3 had the whole corpus and "
              "still returned 'survives.' The spec predicted the opposite -- that only the prosecutorial check would catch the "
              "confident misreading. In this run the prosecutor was the agreeable one. Hypothesis: corpus access gave Check 3 "
              "enough context to rationalize, which is exactly the context contamination the spec guards against in Check 2 but "
              "grants freely to Check 3. That asymmetry looks like a design flaw and is logged for the auditor.")
 },
 "results":results
}
Path('receipts/UE-2026-001.receipts.json').write_text(json.dumps(out,indent=2))

print("SHIPPED", len(shipped), " KILLED", len(killed))
print()
print("KILLED CLAIMS (published):")
for r in killed:
    print(f"  {r['claim_id']:5s} {r['type']}  {r['kill_reason'][:95]}")
print()
print("check2/check3 disagreements:", disagree)
print("killed only by check 2:", c2_unique)
print("killed only by check 3:", c3_unique)
