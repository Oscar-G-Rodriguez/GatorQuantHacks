"""Scheduled, complete stock readout under the committed H21 delivery protocol."""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from .atlas import manifest,done,scheduled,receipt
from .io import ROOT,digest,read_json,write_json,now

PROTOCOL='Hypotheses/H21 - Massive Disclosure Research Atlas/Readout Protocol.md'
PROTOCOL_COMMIT='d4a543e'


def summarize(master,comparisons,inferred):
    if len(master)!=119 or master.category.nunique()!=119:raise ValueError('All119 categories required')
    if comparisons.comparison_id.duplicated().any():raise ValueError('Duplicate original comparison IDs')
    joined=comparisons.copy()
    for block in [63,126]:
        rows=inferred.loc[inferred.block_sessions==block].set_index('comparison_id')
        if not rows.index.is_unique:raise ValueError('Duplicate inference IDs')
        for field in ['romano_wolf_p','pointwise_lower','pointwise_upper','inference_status','finite_resamples','missing_resamples']:
            joined[field+'_'+str(block)]=joined.comparison_id.map(rows[field])
    forecast=joined[joined.group.isin(['labels','patterns','text'])].copy()
    forecast['pattern']=forecast.pattern.fillna('global')
    forecast['baseline']=forecast.baseline.fillna('market')
    # Global inference uses the broad paired loss cohort; tag/pattern inference
    # uses its activation cohort. Never pair an event-only estimate with global CI.
    forecast['loss_improvement']=np.where(forecast.pattern.eq('global'),forecast.mse_improvement,forecast.event_improvement)
    forecast['measured']=forecast.status.eq('measured') & forecast.loss_improvement.notna()
    forecast['positive']=forecast.measured & forecast.loss_improvement.gt(0)
    forecast['both_uncertainty']=forecast.inference_status_63.eq('approximate_exploratory') & forecast.inference_status_126.eq('approximate_exploratory')
    forecast['both_adjustments']=forecast.both_uncertainty & forecast.romano_wolf_p_63.le(.05) & forecast.romano_wolf_p_126.le(.05)
    result=master.copy()
    for field,flag in [('measured_conditional_forecast_cells','measured'),('positive_conditional_forecast_cells','positive'),
                       ('both_block_eligible_conditional_forecast_cells','both_uncertainty')]:
        counts=forecast[forecast.pattern.str.startswith('tag:')].groupby('pattern')[flag].sum()
        result[field]=result.category.map(lambda category:int(counts.get('tag:'+category,0)))
    selected=forecast[forecast.pattern.str.startswith('tag:') & forecast.positive & forecast.both_adjustments].groupby('pattern').size()
    result['positive_cells_passing_both_adjustments']=result.category.map(lambda category:int(selected.get('tag:'+category,0)))
    result['readout_scope']='Overlapping exploratory cell counts; options/full-search placebos pending; no alpha claim'
    keys=['pattern','family','kind','horizon','lag','group','baseline']
    forecast['family']=forecast.family.fillna('global')
    annual=[]
    for key,frame in forecast.groupby(keys,dropna=False,sort=True):
        if frame.year.duplicated().any():raise ValueError('Duplicate yearly forecast cohort')
        row=dict(zip(keys,key));by={int(r.year):r for r in frame.itertuples()}
        for year in [2023,2024,2025]:
            r=by.get(year)
            row['status_'+str(year)]=r.status if r is not None else 'missing'
            row['loss_improvement_'+str(year)]=r.loss_improvement if r is not None else np.nan
            for block in [63,126]:row[f'adjusted_p_{year}_{block}']=getattr(r,'romano_wolf_p_'+str(block)) if r is not None else np.nan
        row['all_three_years_positive']=all(year in by and by[year].positive for year in [2023,2024,2025])
        row['all_three_years_positive_passing_both_adjustments']=row['all_three_years_positive'] and all(by[year].both_adjustments for year in [2023,2024,2025])
        annual.append(row)
    across=pd.DataFrame(annual)
    broad=joined[joined.pattern.isna()].copy()
    return result,joined,broad,across


def run(stage,archive):
    scheduled();stage=Path(stage).resolve();m=manifest(stage);parent=ROOT/m['parent_run']
    if Path(archive).exists():raise ValueError('Preserve earlier readout archives')
    if manifest(parent)['manifest_id']!=m['parent_manifest_id']:raise ValueError('Parent differs')
    if not done(stage,'inference') or not done(parent,'report'):raise ValueError('Verified completed input stages required')
    protocol=ROOT/PROTOCOL
    master=pd.read_csv(parent/'outputs/master.csv');comparisons=pd.read_csv(parent/'outputs/comparisons.csv',low_memory=False)
    inferred=pd.read_csv(stage/'outputs/inference.csv')
    result,joined,broad,across=summarize(master,comparisons,inferred)
    folder=stage/'outputs/readout';folder.mkdir(parents=True,exist_ok=False)
    files=[]
    for name,frame in [('master.csv',result),('comparisons.csv',joined),('broad-panel.csv',broad),('cross-year-forecasts.csv',across)]:
        path=folder/name;frame.to_csv(path,index=False);files.append(path)
    positive=int(across.all_three_years_positive.sum());passing=int(across.all_three_years_positive_passing_both_adjustments.sum())
    summary={'manifest_id':m['manifest_id'],'parent_manifest_id':m['parent_manifest_id'],'protocol_commit':PROTOCOL_COMMIT,
        'protocol_sha256':digest(protocol),'readout_code_sha256':digest(Path(__file__)),'categories':len(result),'comparison_rows':len(joined),
        'cross_year_forecast_groups':len(across),'all_three_years_positive_groups':positive,
        'all_three_years_positive_passing_both_adjustments_groups':passing,'inference_states':inferred.inference_status.value_counts().to_dict(),
        'alpha_claim':False,'complete_atlas':False,'remaining':['Options acquisition/comparisons','499 full-search placebo replicas','Large draw archive verified PC return'],
        'generated_at':now()}
    summary_path=folder/'summary.json';write_json(summary_path,summary);files.append(summary_path)
    text=f'''# Massive disclosure stock atlas — staged findings

The stock search and amended uncertainty calculation have finished. This report includes all119 category definitions and{len(joined):,} comparison rows. It is exploratory evidence from100 supplied companies over2022–2025, with annual evaluation in2023,2024,2025. It does not establish alpha or simulate trading.

## What the calculations show

There are{len(across):,} forecast groups across years. Of these,{positive:,} have measured positive paired forecast-error improvements in all three evaluation years. {passing:,} are also positive and pass both declared Romano–Wolf adjustments in all three years. These groups overlap and share data/models; the counts are not independent signals. The complete cross-year table retains negative, mixed, missing and unsupported years as well.

The confidence table has{int(summary['inference_states'].get('approximate_exploratory',0)):,} eligible block-length cells and{int(summary['inference_states'].get('unsupported',0)):,} unsupported cells. Sparse groups may lack observations in resampled histories even when their point estimates can be measured. Unsupported uncertainty is not evidence that the relationship is absent.

## How to read the files

- `master.csv`: every119 category, definitions, coverage and overlapping conditional forecast counts. A category's count is not a category-level p-value.
- `comparisons.csv`: every original comparison joined to amended uncertainty by exact ID. Raw response means stay descriptive; ordinary/component responses are matched contrasts. Forecast-error differences have squared fractional-return units.
- `broad-panel.csv`: all global model/baseline readings on their declared paired observations.
- `cross-year-forecasts.csv`: every label/pattern/text forecast group with each year's result. Positive means lower paired forecast error. Category-conditioned results describe the whole augmentation on those events; they do not isolate that label's causal contribution.

## What remains before a stronger claim

Full499-search scrambled-date placebos and complete option-priced comparisons remain pending. A possible mechanism still needs a separate committed economic/execution plan and genuinely unseen evidence before strategy code or a backtest. The static universe has survivor/selection concerns; historical label delivery time is unverified, so filing+1 aligned-session timing is assumed. Prior adaptive exploration remains disclosed. The exposed2026 period is not fresh confirmation, and the organizer's sealed interval is excluded. Negative or inconclusive findings remain valid outcomes of the atlas.

Inputs and outputs are identified by `summary.json` and the hash-verified `readout` receipt. The separately returned larger draw archive remains part of final transfer acceptance.
'''
    note=folder/'Findings.md';note.write_text(text,encoding='utf-8',newline='\n');files.append(note)
    receipt(stage,'readout',files,extra={'protocol_sha256':digest(protocol),'readout_code_sha256':digest(Path(__file__))})
    hashes={p.relative_to(stage).as_posix():digest(p) for p in files+[stage/'manifest.json',stage/'receipts/readout.json']}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for name,h in hashes.items():
            raw=(stage/name).read_bytes()
            if digest(stage/name)!=h:raise ValueError('Readout output changed')
            zipped.writestr(name,raw)
        zipped.writestr('RETURN-RECEIPT.json',json.dumps({'manifest_id':m['manifest_id'],'files':hashes,'scope':'Complete staged stock readout; options and full-search placebos pending'}))
    print(json.dumps({'sha256':digest(archive),'members':len(hashes),'summary':summary}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--archive',required=True);a=p.parse_args();run(a.stage,a.archive)
