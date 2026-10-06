"""Render verified returned tables; no research calculations or model fitting."""
import argparse
import csv
import html
import json
from pathlib import Path
from .atlas import manifest
from .io import digest,now,read_json,write_json

FIELDS=['pattern','group','kind','horizon','lag','year','validation_activations','validation_issuers',
        'response_mean','event_improvement','mse_improvement','romano_wolf_p_63','romano_wolf_p_126','status','reason','comparison_id','baseline',
        'inference_status_63','inference_status_126','finite_resamples_63','finite_resamples_126',
        'pointwise_lower_63','pointwise_upper_63','pointwise_lower_126','pointwise_upper_126']


def returned_inference(stage,parent_id):
    stage=Path(stage).resolve();m=manifest(stage,allow_frozen=True)
    if m.get('parent_manifest_id')!=parent_id:raise ValueError('Uncertainty belongs to another stock parent')
    if not list((stage/'return-verifications').glob('*.json')):raise ValueError('Verify returned uncertainty first')
    receipt=read_json(stage/'receipts/inference.json')
    if receipt['manifest_id']!=m['manifest_id'] or receipt['state']!='completed':raise ValueError('Unverified uncertainty receipt')
    for name,h in receipt['files'].items():
        if digest(stage/name)!=h:raise ValueError('Uncertainty output changed')
    rows={}
    with (stage/'outputs/inference.csv').open(newline='',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            key=(row['comparison_id'],row['block_sessions'])
            if key in rows:raise ValueError('Duplicate inference comparison')
            rows[key]=row
    return rows,{'manifest_id':m['manifest_id'],'method':m['method'],'receipt_sha256':digest(stage/'receipts/inference.json'),
                 'inference_sha256':digest(stage/'outputs/inference.csv'),'stage':str(stage)}


def render(run,output=None,uncertainty=None):
    run=Path(run).resolve();m=manifest(run,allow_frozen=True)
    if not list((run/'return-verifications').glob('*.json')):raise ValueError('Verify returned evidence before rendering')
    receipt=read_json(run/'receipts/report.json')
    if receipt['manifest_id']!=m['manifest_id'] or receipt['state']!='completed':raise ValueError('Unverified report identity')
    for name,h in receipt['files'].items():
        if digest(run/name)!=h:raise ValueError('Returned report changed')
    inferred,inference_provenance=returned_inference(uncertainty,m['manifest_id']) if uncertainty else ({},None)
    out=Path(output).resolve() if output else run/'outputs/viewer-v1'
    if not out.is_relative_to(run/'outputs'):raise ValueError('Viewer must be a derivative within this run outputs')
    out.mkdir(parents=True,exist_ok=False);(out/'cells').mkdir()
    with (run/'outputs/master.csv').open(newline='',encoding='utf-8') as f:master=list(csv.DictReader(f))
    if len(master)!=119 or len({r['category'] for r in master})!=119:raise ValueError('Every category must appear')
    shards={};handles={};counts={}
    try:
        with (run/'outputs/comparisons.csv').open(newline='',encoding='utf-8') as f:
            for row in csv.DictReader(f):
                for block in ['63','126']:
                    added=inferred.get((row['comparison_id'],block))
                    if added:
                        for field in ['romano_wolf_p','inference_status','finite_resamples','pointwise_lower','pointwise_upper']:
                            row[field+'_'+block]=added[field]
                    elif row.get('group')=='response_response':row['inference_status_'+block]='descriptive'
                    elif row.get('group') in ['market','option']:row['inference_status_'+block]='baseline'
                    elif row['status']!='measured':row['inference_status_'+block]='unsupported'
                key=(row['kind'],row['horizon'],row['lag']);name='-'.join(key)+'.js'
                if key not in handles:
                    handles[key]=(out/'cells'/name).open('w',encoding='utf-8',newline='\n')
                    handles[key].write('window.atlasShard([');counts[key]=0;shards[key]=name
                handles[key].write((',' if counts[key] else '')+json.dumps([row.get(k,'') for k in FIELDS],ensure_ascii=True).replace('</','<\\/'))
                counts[key]+=1
    finally:
        for stream in handles.values():stream.write(']);\n');stream.close()
    summary=read_json(run/'outputs/summary.json');complete=sum(v=='completed' for v in summary['core_task_states'].values())
    categories=''.join('<option value="'+html.escape(r['category'])+'">'+html.escape(r['category'].replace('_',' '))+'</option>' for r in master)
    rows=''.join('<tr><td><button class="category" data-category="'+html.escape(r['category'])+'">'+html.escape(r['category'].replace('_',' '))+'</button><small>'+html.escape(r['description'])+'</small></td>'+''.join('<td>'+html.escape(r.get(k,''))+'</td>' for k in ['filings','issuers','filings_2022','filings_2023','filings_2024','filings_2025','measured_forecast_cells','evidence_status'])+'</tr>' for r in master)
    payload={'fields':FIELDS,'shards':[{'kind':k[0],'horizon':k[1],'lag':k[2],'file':'cells/'+v,'rows':counts[k]} for k,v in shards.items()]}
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Massive Disclosure Research Atlas</title>
<style>body{margin:0;background:#f4f7fb;color:#16243a;font:15px system-ui}header{padding:30px max(24px,5vw);background:#11213a;color:white}h1{margin:8px 0;font-size:32px}main{padding:24px max(24px,5vw)}.banner{background:#fff2cf;border-left:4px solid #bd8300;padding:16px;line-height:1.6}.filters{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}label{display:grid;gap:5px;color:#38506c}input,select{padding:9px;border:1px solid #aebed3;background:white;border-radius:6px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:10px;border-bottom:1px solid #dce4ef;text-align:left;vertical-align:top}th{background:#e7edf6;white-space:nowrap}small{display:block;max-width:460px;color:#51647b;margin-top:6px}.scroll{overflow:auto;max-height:620px;border:1px solid #dce4ef}.category{border:0;background:none;color:#096fa7;padding:0;text-align:left;font:inherit;cursor:pointer}a{color:#096fa7}header a{color:#a9defd}.metrics{display:flex;gap:30px;flex-wrap:wrap;margin:16px 0}.metrics strong{display:block;font-size:25px}h2{margin-top:32px}.muted{color:#51647b}#status{min-height:24px}</style>
<header><div>MASSIVE · H21 · DEVELOPMENT RESEARCH</div><h1>Disclosure Research Atlas</h1><p>100 supplied companies · 2022–2025 · all 119 disclosure types</p><div class="metrics"><div><strong>119</strong>Category definitions</div><div><strong>CORE_COUNT / 128</strong>Stock search tasks returned</div></div></header>
<main><div class="banner">Exploratory results. Static-universe survivorship and retrospective label availability limit interpretation. Multiple-testing uncertainty, option coverage and full-search placebos may still be pending. This atlas does not simulate trading or establish net alpha.</div>
<p><a href="../master.csv">119-row master table</a> · <a href="../comparisons.csv">Every comparison</a> · <a href="../trials.csv">All model trials</a> · <a href="../patterns.csv">Combination and sequence inventory</a> · <a href="../quality.json">Source details</a> · <a href="provenance.json">Viewer provenance</a></p>
<h2>Category coverage</h2><label>Find a category or definition<input id="masterSearch" placeholder="e.g. CEO, compensation, debt"></label><p id="masterCount"></p><div class="scroll"><table><thead><tr><th>Type and definition</th><th>Filings</th><th>Issuers</th><th>2022</th><th>2023</th><th>2024</th><th>2025</th><th>Measured cells</th><th>Evidence status</th></tr></thead><tbody id="master">MASTER_ROWS</tbody></table></div>
<h2>Outcomes and forecast comparisons</h2><p class="muted">Choose one outcome, horizon and delay, then explore categories or combinations. Positive loss improvement means lower forecast error on the same observations. Response and loss values have different units. Uncertainty marked pending has not been calculated for this returned stage.</p>
<div class="filters"><label>Outcome<select id="kind"><option value="return">Signed return</option><option value="absolute">Absolute return</option><option value="volatility">RMS volatility</option><option value="downside">Maximum downside excursion</option><option value="premium_30">30-day option premium change</option><option value="premium_60">60-day option premium change</option><option value="premium_120">120-day option premium change</option></select></label><label>Horizon (sessions)<select id="horizon">HORIZONS</select></label><label>Additional delay (sessions)<select id="lag">LAGS</select></label><label>Category<select id="category"><option value="">Every category / global</option>CATEGORIES</select></label><label>Pattern or feature group<input id="pattern" placeholder="e.g. seq21, text, CEO"></label><label>Evidence<select id="evidence"><option value="">Every status</option><option>measured</option><option>unsupported</option><option>failed</option></select></label><label>Minimum validation activations<input id="support" type="number" min="0" value="0"></label></div>
<p id="status"></p><div class="scroll"><table><thead><tr><th>Pattern / group</th><th>Year</th><th>Activations / issuers</th><th>Response</th><th>Loss improvement</th><th>Adjusted p (63 / 126)</th><th>Evidence</th></tr></thead><tbody id="results"></tbody></table></div>
<p class="muted">All returned cells remain in the linked CSV. The viewer displays the first 500 matches in source order, without ranking favorable results.</p></main>
<script>const config=CONFIG;let token=0,busy=false,pending=false;function escapeText(v){let e=document.createElement('span');e.textContent=v??'';return e.innerHTML;}function number(v){return v!==''&&Number.isFinite(Number(v))?Number(v).toPrecision(5):'—';}function coverage(){let q=document.getElementById('masterSearch').value.toLowerCase(),n=0;for(let r of document.querySelectorAll('#master tr')){r.hidden=!r.textContent.toLowerCase().includes(q);if(!r.hidden)n++;}document.getElementById('masterCount').textContent=n+' of 119 categories shown';}
async function refresh(){if(busy){pending=true;token++;return;}busy=true;try{let current=++token,kind=document.getElementById('kind').value,h=document.getElementById('horizon').value,lag=document.getElementById('lag').value,category=document.getElementById('category').value,q=document.getElementById('pattern').value.toLowerCase(),evidence=document.getElementById('evidence').value,min=Number(document.getElementById('support').value);let matches=0,shown=[];document.getElementById('status').textContent='Reading returned cells…';document.getElementById('results').innerHTML='';let shards=config.shards.filter(s=>s.kind===kind&&s.horizon===h&&s.lag===lag);for(let shard of shards){await new Promise(resolve=>{let script=document.createElement('script');window.atlasShard=rows=>{if(current!==token)return;for(let a of rows){let r=Object.fromEntries(config.fields.map((k,i)=>[k,a[i]]));if((category&&!String(r.pattern).includes(category))||(q&&!String(r.pattern+' '+r.group).toLowerCase().includes(q))||(evidence&&r.status!==evidence)||Number(r.validation_activations||0)<min)continue;matches++;if(shown.length<500)shown.push(r);}};script.src=shard.file;script.onload=()=>{script.remove();resolve();};script.onerror=()=>{script.remove();resolve();};document.body.appendChild(script);});if(current!==token)return;}document.getElementById('status').textContent=shards.length?matches+' matching cells; showing '+shown.length+'.':'No returned cells for this setting; coverage may be pending.';document.getElementById('results').innerHTML=shown.map(r=>'<tr><td>'+escapeText(r.pattern||'Global')+'<small>'+escapeText(r.group)+' vs '+escapeText(r.baseline||'declared comparison')+'</small></td><td>'+escapeText(r.year)+'</td><td>'+number(r.validation_activations)+' / '+number(r.validation_issuers)+'</td><td>'+number(r.response_mean)+'</td><td>'+number(r.event_improvement||r.mse_improvement)+'</td><td>'+escapeText(r.romano_wolf_p_63||'pending')+' / '+escapeText(r.romano_wolf_p_126||'pending')+'</td><td>'+escapeText(r.status)+'<small>'+escapeText(r.reason)+'</small></td></tr>').join('');}finally{busy=false;if(pending){pending=false;refresh();}}}
for(let id of ['kind','horizon','lag','category','pattern','evidence','support'])document.getElementById(id).onchange=refresh;document.getElementById('masterSearch').oninput=coverage;for(let b of document.querySelectorAll('.category'))b.onclick=()=>{document.getElementById('category').value=b.dataset.category;refresh();document.getElementById('kind').scrollIntoView({behavior:'smooth'});};coverage();refresh();</script></html>'''
    page=page.replace('CORE_COUNT',str(complete)).replace('MASTER_ROWS',rows).replace('CATEGORIES',categories)
    page=page.replace('HORIZONS',''.join(f'<option{chr(32)+"selected" if h==5 else ""}>{h}</option>' for h in m['settings']['horizons']))
    page=page.replace('LAGS',''.join(f'<option>{lag}</option>' for lag in m['settings']['lags'])).replace('CONFIG',json.dumps(payload).replace('</','<\\/'))
    page=page.replace('<th>Response</th>','<th>Response / matched contrast</th>')
    page=page.replace("escapeText(r.romano_wolf_p_63||'pending')", "escapeText(r.romano_wolf_p_63||r.inference_status_63||'pending')")
    page=page.replace("escapeText(r.romano_wolf_p_126||'pending')", "escapeText(r.romano_wolf_p_126||r.inference_status_126||'pending')")
    if inference_provenance:
        page=page.replace('Multiple-testing uncertainty, option coverage and full-search placebos may still be pending.',
            'Amended year-stratified multiple-testing uncertainty has returned. Option coverage and the 499 full-search placebos remain pending. Sparse uncertainty cells remain explicitly unsupported.')
    (out/'index.html').write_text(page,encoding='utf-8')
    write_json(out/'provenance.json',{'manifest_id':m['manifest_id'],'created_at':now(),'viewer_code_sha256':digest(Path(__file__)),
        'source_report_sha256':digest(run/'receipts/report.json'),'source_comparisons_sha256':digest(run/'outputs/comparisons.csv'),'uncertainty_stage':inference_provenance,
        'scope':'Display-only derivative of verified returned tables; no research computation','files':{p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}})
    return {'viewer':str(out/'index.html'),'shards':len(shards),'rows_retained':sum(counts.values())}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output');p.add_argument('--uncertainty');a=p.parse_args();print(json.dumps(render(a.run,a.output,a.uncertainty)))
