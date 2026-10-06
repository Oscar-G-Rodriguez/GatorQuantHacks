"""Synthetic H21 checks; no sponsor data or real research calculation on PC."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import sparse
from discovery.atlas_features import pattern_catalog,eligible_columns,TextFeatures,sessions,build_panel,scramble,normalize,fitting_catalog
from discovery.atlas_statistics import outer_masks,romano_wolf,support,joint_weights
from discovery.atlas_data import Store,RequestBudget,NoRedirect
from discovery.atlas import scheduled,cells

SYNTHETIC_REMOTE = '/blue/test-allocation/test-user/quanthacks/discovery'


def config():
    return {"start":"2022-01-01","end":"2025-12-31","tickers":["A","B"],"benchmark":"SPY","categories":["a","b","c","empty"],
            "horizons":[1,2,63],"lags":[0,1,3,5],"sequence_windows":[5,21,63],"maximum_pattern_length":4,
            "train_min_activations":2,"train_min_issuers":2,"text_min_df":2,"text_max_features":100,"text_components":64,"seed":17}


class AtlasTests(unittest.TestCase):
    def test_inference_summary_return_excludes_large_draws(self):
        import json,zipfile
        from discovery import atlas_summary_return
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';(run/'outputs').mkdir(parents=True);(run/'receipts').mkdir();(run/'uncertainty').mkdir()
            (run/'manifest.json').write_text('{}');table=run/'outputs/inference.csv';table.write_text('synthetic evidence')
            (run/'uncertainty/draws.npz').write_text('large retained draw evidence')
            (run/'receipts/inference.json').write_text(json.dumps({'files':{'outputs/inference.csv':digest(table)}}))
            with patch.object(atlas_summary_return,'scheduled'),patch.object(atlas_summary_return,'manifest',return_value={'manifest_id':'synthetic'}),patch.object(atlas_summary_return,'done',return_value=True):
                archive=root/'summary.zip';result=atlas_summary_return.export_summary(run,archive)
                self.assertEqual(result['members'],3)
                with zipfile.ZipFile(archive) as a:self.assertNotIn('uncertainty/draws.npz',a.namelist())
                table.write_text('changed')
                with self.assertRaises(ValueError):atlas_summary_return.export_summary(run,root/'changed.zip')

    def test_stage_return_excludes_live_unfinished_outputs_and_checks_nested_files(self):
        import json,zipfile
        from discovery import atlas_return
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';(run/'receipts').mkdir(parents=True);(run/'tasks/core-000/2023').mkdir(parents=True);(run/'tasks/core-001').mkdir(parents=True)
            (run/'manifest.json').write_text('{}');finished=run/'tasks/core-000/2023/result.txt';finished.write_text('verified')
            checkpoint=finished.parent/'complete.json';checkpoint.write_text(json.dumps({'files':{'result.txt':digest(finished)}}))
            (run/'tasks/core-001/live.npz').write_text('currently writing')
            (run/'receipts/core-000.json').write_text(json.dumps({'manifest_id':'synthetic','state':'completed','stage':'core-000','files':{'tasks/core-000/2023/complete.json':digest(checkpoint)}}))
            with patch.object(atlas_return,'manifest',return_value={'manifest_id':'synthetic'}),patch.object(atlas_return,'scheduled'),patch.object(atlas_return,'ROOT',root):
                archive=root/'return.zip';atlas_return.export_completed(run,archive)
                with zipfile.ZipFile(archive) as a:
                    self.assertIn('tasks/core-000/2023/result.txt',a.namelist());self.assertNotIn('tasks/core-001/live.npz',a.namelist())
                finished.write_text('changed')
                with self.assertRaises(ValueError):atlas_return.export_completed(run,root/'another.zip')

    def test_display_viewer_preserves_all_cells_and_requires_return_hashes(self):
        import csv,json
        from discovery import atlas_viewer
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)/'run';(run/'outputs').mkdir(parents=True);(run/'receipts').mkdir();(run/'return-verifications').mkdir();(run/'return-verifications/verified.json').write_text('{}')
            master=run/'outputs/master.csv'
            with master.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['category','description']);w.writeheader();w.writerows({'category':'type'+str(i),'description':'Source definition'} for i in range(119))
            comp=run/'outputs/comparisons.csv'
            with comp.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['comparison_id','kind','horizon','lag','status']);w.writeheader();w.writerows({'comparison_id':str(i),'kind':'return','horizon':5,'lag':0,'status':s} for i,s in enumerate(['measured','unsupported','failed']))
            (run/'outputs/summary.json').write_text(json.dumps({'core_task_states':{'core-000':'completed'}}))
            files={p.relative_to(run).as_posix():digest(p) for p in [master,comp,run/'outputs/summary.json']}
            (run/'receipts/report.json').write_text(json.dumps({'manifest_id':'synthetic','state':'completed','files':files}))
            m={'manifest_id':'synthetic','settings':{'horizons':[1,5],'lags':[0,1]}}
            with patch.object(atlas_viewer,'manifest',return_value=m):
                result=atlas_viewer.render(run);self.assertEqual(result['rows_retained'],3)
                data=(run/'outputs/viewer-v1/cells/return-5-0.js').read_text()
                self.assertIn('unsupported',data);self.assertIn('failed',data)
                stage=Path(td)/'uncertainty';(stage/'outputs').mkdir(parents=True);(stage/'receipts').mkdir();(stage/'return-verifications').mkdir()
                (stage/'return-verifications/verified.json').write_text('{}');inferred=stage/'outputs/inference.csv'
                inferred.write_text('comparison_id,block_sessions,romano_wolf_p,inference_status,finite_resamples,pointwise_lower,pointwise_upper\n0,63,0.8,approximate_exploratory,9999,-1,1\n')
                (stage/'receipts/inference.json').write_text(json.dumps({'manifest_id':'uncertainty','state':'completed','files':{'outputs/inference.csv':digest(inferred)}}))
                um={'manifest_id':'uncertainty','parent_manifest_id':'synthetic','method':'synthetic-method'}
                with patch.object(atlas_viewer,'manifest',side_effect=lambda path,**kw: um if Path(path)==stage else m):
                    joined=atlas_viewer.render(run,run/'outputs/viewer-joined',stage)
                    self.assertEqual(joined['rows_retained'],3)
                    self.assertIn('approximate_exploratory',(run/'outputs/viewer-joined/cells/return-5-0.js').read_text())
                    um['parent_manifest_id']='wrong'
                    with self.assertRaises(ValueError):atlas_viewer.returned_inference(stage,'synthetic')
                    um['parent_manifest_id']='synthetic';inferred.write_text('changed')
                    with self.assertRaises(ValueError):atlas_viewer.returned_inference(stage,'synthetic')
                comp.write_text('changed')
                with self.assertRaises(ValueError):atlas_viewer.render(run,run/'outputs/viewer-v2')

    def test_options_resume_skips_completed_anchors(self):
        import json
        from discovery import atlas_options
        class FakeStore:
            interrupt=True
            def __init__(self,*args):self.entries={};self.failures=[];self.calls=0
            def pages(self,*args,**kwargs):
                if args[1]=='/v3/reference/options/contracts':assert args[2]['expired']=='false'
                if '/aggs/ticker/' in args[1]:return [{'t':1641186000000,'c':100.}]
                self.calls+=1
                if self.interrupt and self.calls>1:raise RequestBudget('synthetic interruption')
                return None
        anchors=[{'ticker':x,'date':'2022-01-03','stock_close':100.,'role':'event'} for x in ['A','B','C']]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);requests=root/'requests.json';requests.write_text(json.dumps(anchors))
            with patch.object(atlas_options,'settings',return_value=config()),patch.object(atlas_options,'Store',FakeStore):
                with self.assertRaises(RequestBudget):atlas_options.acquire(requests,root/'source')
                FakeStore.interrupt=False;atlas_options.acquire(requests,root/'source')
            source=json.loads((root/'source/options-source.json').read_text())
            self.assertTrue(source['complete']);self.assertEqual(source['calls'],2);self.assertEqual(len(source['records']),3)
            self.assertEqual(len(source['previous_manifest_hashes']),1)

    def test_option_strikes_use_nominal_spot_not_later_split_adjustment(self):
        from discovery.atlas_options import nominal_spot,select
        from types import SimpleNamespace
        store=SimpleNamespace(pages=lambda *a,**kw:[{'t':1641186000000,'c':2000.}])
        anchor={'ticker':'A','date':'2022-01-03','stock_close':100.}
        corrected=nominal_spot(store,anchor,config())
        self.assertEqual(corrected['stock_close'],2000.);self.assertEqual(corrected['adjusted_stock_close'],100.)
        contracts=[{'ticker':str(k)+side,'strike_price':k,'expiration_date':'2022-02-04','contract_type':side,'shares_per_contract':100,'exercise_style':'american'}
                   for k in [100,2000] for side in ['call','put']]
        c={**config(),'option_buckets':{'30':[21,45]},'option_otm_distance':.05,'option_otm_tolerance':.02}
        chosen=select(contracts,corrected,c)
        self.assertEqual(chosen['30']['legs']['atm_call']['strike_price'],2000.)

    def test_compressed_tasks_remain_verified_without_expansion(self):
        import json,zipfile,hashlib
        from discovery import atlas_jobs
        from discovery.atlas_evidence import Evidence
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir();archive=root/'returned.zip'
            name='tasks/placebo-000-000/result.json';raw=b'{"result":"synthetic"}'
            receipt=json.dumps({'manifest_id':'synthetic','state':'completed','files':{name:hashlib.sha256(raw).hexdigest()}}).encode()
            files={name:raw,'receipts/placebo-000-000.json':receipt};r={'manifest_id':'synthetic','files':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}
            with zipfile.ZipFile(archive,'w') as a:
                for n,v in files.items():a.writestr(n,v)
                a.writestr('RETURN-RECEIPT.json',json.dumps(r))
            with patch.object(atlas_jobs,'manifest',return_value={'manifest_id':'synthetic'}):
                result=atlas_jobs.import_results(archive,run,digest(archive),True)
            self.assertEqual(result['compressed_task_members'],2);self.assertFalse((run/name).exists())
            self.assertTrue(archive.exists())
            self.assertTrue(Evidence(run).completed('placebo-000-000','synthetic'))
            saved=next((run/'archives').glob('*.zip'));saved.write_bytes(b'changed')
            with self.assertRaises(ValueError):Evidence(run).completed('placebo-000-000','synthetic')

    def test_option_quote_samples_are_bounded_and_outcome_independent(self):
        from discovery.atlas_options import quote_samples
        anchors=[{'ticker':'A'+str(i),'date':'2022-01-03','role':'event','future_outcome':i} for i in range(100)]
        chosen=quote_samples(anchors,17,8);self.assertEqual(len(chosen),8)
        changed=[{**a,'future_outcome':-a['future_outcome']} for a in anchors[::-1]]
        self.assertEqual(chosen,quote_samples(changed,17,8))

    def test_scheduler_ledger_scopes_owned_jobs_and_records_cancellation_once(self):
        import json,csv
        from discovery import atlas_jobs
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';(run/'scheduler').mkdir(parents=True);(run/'return-verifications').mkdir();(run/'return-verifications/verified.json').write_text('{}')
            (run/'transfer-observation.json').write_text(json.dumps({'submitted_jobs':{'pilot':'123'}}))
            (run/'scheduler/scheduler-pilot.txt').write_text('JobID|JobName|State\n123_0|h21-pilot|CANCELLED\n999|other|FAILED\n')
            (root/'Hypotheses').mkdir();ledger=root/'Hypotheses/EXPERIMENTS.csv'
            fields=['experiment_id','registered_at','hypothesis_id','registration_commit','code_commit','sample_or_fold','parameters','signal_and_fill_timing','cost_model','data_identity','outcome','evidence_path','notes']
            ledger.write_text(','.join(fields)+'\n')
            m={'manifest_id':'synthetic','created_at':'synthetic','code_commit':'synthetic','plan_commit':'synthetic'}
            with patch.object(atlas_jobs,'ROOT',root),patch.object(atlas_jobs,'manifest',return_value=m):
                self.assertEqual(atlas_jobs.record(run)['new_records'],1)
                self.assertEqual(atlas_jobs.record(run)['new_records'],0)
            with ledger.open() as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['outcome'],'CANCELLED');self.assertNotIn('999',rows[0]['parameters'])

    def test_large_ledger_indexes_every_variant_without_dropping_statuses(self):
        import json,csv
        from discovery import atlas_jobs
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';(run/'tasks/core-000').mkdir(parents=True);(run/'return-verifications').mkdir();(run/'return-verifications/verified.json').write_text('{}')
            table=run/'tasks/core-000/comparisons.csv';table.write_text('status,value\nmeasured,-1\nunsupported,\nfailed,\n')
            (root/'Hypotheses').mkdir();ledger=root/'Hypotheses/EXPERIMENTS.csv'
            fields=['experiment_id','registered_at','hypothesis_id','registration_commit','code_commit','sample_or_fold','parameters','signal_and_fill_timing','cost_model','data_identity','outcome','evidence_path','notes']
            ledger.write_text(','.join(fields)+'\n')
            m={'manifest_id':'synthetic','created_at':'synthetic','code_commit':'synthetic','plan_commit':'synthetic'}
            with patch.object(atlas_jobs,'ROOT',root),patch.object(atlas_jobs,'manifest',return_value=m):
                self.assertEqual(atlas_jobs.record(run,True)['new_records'],1)
                self.assertEqual(atlas_jobs.record(run,True)['new_records'],0)
            index=json.loads((run/'audit/ledger-variant-index.json').read_text())['tables'][0]
            self.assertEqual(index['complete_variant_rows'],3);self.assertEqual(index['sha256'],digest(table))
            self.assertEqual(index['states'],{'measured':1,'unsupported':1,'failed':1})
            with ledger.open() as f:self.assertEqual(len(list(csv.DictReader(f))),1)

    def test_option_future_marks_only_populate_targets_and_end_bounds(self):
        from discovery.atlas import option_targets
        dates=pd.to_datetime(['2025-12-30','2025-12-31'])
        panel=pd.DataFrame({'ticker':['A','A'],'date':dates,'target_end_1':[dates[1],pd.NaT]})
        c={'option_buckets':{'30':[21,45]},'horizons':[1]}
        readings=[{'ticker':'A','date':str(d.date()),'bucket':'30','premium_change_1':.2} for d in dates]
        out=option_targets(panel,readings,c)
        self.assertEqual(out['premium_30_1'][0],.2);self.assertTrue(np.isnan(out['premium_30_1'][1]))
        self.assertEqual(set(panel.columns),{'ticker','date','target_end_1'})

    def test_bounded_quote_is_one_sample_without_full_stream_pagination(self):
        with tempfile.TemporaryDirectory() as td,patch.dict('os.environ',{'MASSIVE_API_KEY':'synthetic'}):
            store=Store(td)
            with patch.object(store,'_get',return_value={'results':[{'sip_timestamp':123}],'next_url':'https://api.massive.com/next'}) as get:
                rows=store.pages('synthetic quote','/v3/quotes/O%3ATEST',{'limit':1},paginate=False)
                self.assertEqual(len(rows),1);self.assertEqual(get.call_count,1)
            self.assertEqual(next(iter(store.entries.values()))['scope'],'bounded_first_page')

    def test_interrupted_cell_resumes_only_unfinished_years(self):
        from discovery import atlas
        from types import SimpleNamespace
        c={**config(),'fold_years':[2023,2024,2025],'horizons':[1],'lags':[0]}
        panel=pd.DataFrame({'issuer':['i']*4,'session':range(4),'date':pd.date_range('2022-01-03',periods=4),'weight':[1.]*4})
        with tempfile.TemporaryDirectory() as td,patch.object(atlas,'scheduled'),patch.object(atlas,'prepared',return_value=(panel,[],c)),\
                patch.object(atlas,'done',return_value=False),patch.object(atlas,'pattern_catalog',return_value=[]),\
                patch.object(atlas,'feature_matrix',return_value=(sparse.csc_matrix((4,0)),None,None,np.zeros(4,bool))),\
                patch.object(atlas,'response_cell',return_value=([],[])),patch.object(atlas,'receipt'),\
                patch.dict('sys.modules',{'resource':SimpleNamespace(RUSAGE_SELF=0,getrusage=lambda _:SimpleNamespace(ru_maxrss=1))}):
            def fitted(*args,**kwargs):return ([{'year':kwargs['config']['fold_years'][0]}],[],[]) if 'config' in kwargs else ([{'year':args[2]['fold_years'][0]}],[],[])
            with patch.object(atlas,'forecast_cell',side_effect=[([{'year':2023}],[],[]),RuntimeError('synthetic interruption')]):
                with self.assertRaises(RuntimeError):atlas.core(td,0)
            self.assertTrue((Path(td)/'tasks/core-000/2023/complete.json').exists())
            with patch.object(atlas,'forecast_cell',side_effect=fitted) as fit:
                atlas.core(td,0);self.assertEqual(fit.call_count,2)
            (Path(td)/'tasks/core-000/2023/comparisons.json').write_text('changed')
            with patch.object(atlas,'forecast_cell') as fit:
                with self.assertRaises(ValueError):atlas.core(td,0)
                fit.assert_not_called()

    def test_retry_arrays_exclude_verified_completed_cells(self):
        from discovery import atlas_jobs
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir()
            m={'manifest_id':'synthetic','settings':{'horizons':[1],'lags':[0],'resamples':9999,'resample_batch':100,'placebos':499}}
            with patch.object(atlas_jobs,'ROOT',root),patch.object(atlas_jobs,'manifest',return_value=m),patch.object(atlas_jobs,'remote_base',return_value=SYNTHETIC_REMOTE),patch('discovery.atlas_evidence.Evidence.completed',side_effect=lambda label,*args:label=='core-001'):
                self.assertEqual(atlas_jobs.missing_tasks(run,'search'),[0,2,3])
                result=atlas_jobs.jobs(run,SYNTHETIC_REMOTE+'/atlas-synthetic','search',4,8,True)
                folder=Path(result['scripts']);self.assertIn('--array=0,2,3%4',(folder/'core.sbatch').read_text())
                self.assertIn(folder.name+'/return.sbatch',(folder/'submit.sh').read_text())
                self.assertIn('submission-'+folder.name+'.txt',(folder/'return.sbatch').read_text())

    def test_prior_frequency_counts_filings_and_recency_excludes_current(self):
        from discovery.atlas_features import feature_matrix
        c=config();dates=pd.bdate_range('2022-01-03',periods=80)
        panel=pd.DataFrame({'ticker':['A']*80,'issuer':['i']*80,'date':dates})
        fs=[{'issuer':'i','accession':name,'session':s,'rows':[s],'categories':['a'],'text':''}
            for name,s in [('first',64),('second',64),('third',67)]]
        cat=pattern_catalog(fs,c)
        with patch('discovery.atlas_features.sessions',return_value=dates):
            matrix,contexts,_,_=feature_matrix(panel,fs,cat,c)
        tag=next(i for i,p in enumerate(cat) if p['name']=='tag:a');tag_entries=[p for p in cat if p['family']=='tag']
        history=next(i for i,p in enumerate(tag_entries) if p['name']=='tag:a');tags=len(tag_entries)
        self.assertEqual(matrix[64,tag],1)
        self.assertEqual(contexts[65,history],2)
        self.assertEqual(contexts[67,history],2)
        self.assertEqual(contexts[67,3*tags+history],3)
        self.assertEqual(contexts[68,3*tags+history],1)
        self.assertTrue(np.isnan(contexts[62,3*tags+history]))

    def test_credential_destination_requires_https_without_userinfo(self):
        store=object.__new__(Store)
        for url in ['http://api.massive.com/a','https://user@api.massive.com/a','https://api.massive.com:444/a','https://api.massive.com/a?apiKey=secret']:
            with self.assertRaises(ValueError):store._get(url,'synthetic boundary')

    def test_multiple_excerpts_preserved_without_extra_events(self):
        c=config();row={"cik":"1","accession_number":"x","tertiary_category":"a","filing_date":"2022-01-03","supporting_text":"first passage"}
        source={"settings":c,"objects":{},"disclosure_collections":[{"object_id":"f","tickers":["A"]}]}
        prices,events,issues=normalize(source,{"f":[row,{**row,"supporting_text":"second passage"},row]})
        self.assertEqual(len(events),1);self.assertEqual(events[0]["excerpts"],["first passage","second passage"])
        self.assertIn("second passage",events[0]["text"]);self.assertEqual(len(issues),1)

    def test_duplicate_filings_and_strict_sequence_order(self):
        c=config();f=[{"issuer":"i","accession":"x","session":10,"rows":[10],"categories":["a","b"]},
                      {"issuer":"i","accession":"y","session":10,"rows":[10],"categories":["c"]},
                      {"issuer":"i","accession":"z","session":12,"rows":[12],"categories":["c"]}]
        p={r["name"]:r for r in pattern_catalog(f,c,20)}
        self.assertIn("tag:empty",p);self.assertIn("set:a&b",p)
        self.assertEqual(p["seq5:a>c"]["rows"],[12]);self.assertNotIn("seq5:a>b",p)
        self.assertNotIn("seq5:a>c>c",p)

    def test_share_classes_do_not_meet_activation_floor_twice(self):
        c=config();panel=pd.DataFrame({"issuer":["i","i","j","j"],"date":pd.to_datetime(["2022-01-03"]*4)})
        m=sparse.csr_matrix(np.ones((4,1)));self.assertEqual(eligible_columns(m,panel,np.ones(4,bool),c),[0])
        c["train_min_activations"]=3;self.assertEqual(eligible_columns(m,panel,np.ones(4,bool),c),[])
        self.assertEqual(support(panel,np.ones(4,bool),np.ones(4,bool))["activations"],2)

    def test_inventory_pruning_preserves_every_tag(self):
        c=config();cat=[{"name":"tag:empty","family":"tag","source_filings":0,"source_issuers":0},
            {"name":"set:a&b","family":"itemset","source_filings":1,"source_issuers":1},
            {"name":"seq5:a>b","family":"sequence","source_filings":10,"source_issuers":2}]
        self.assertEqual([p["name"] for p in fitting_catalog(cat,c)],["tag:empty","seq5:a>b"])

    def test_synthetic_forecast_pairs_identical_outer_observations(self):
        from discovery.atlas_statistics import forecast_cell
        from discovery.atlas_features import CONTROLS
        dates=pd.bdate_range('2022-01-03','2023-12-29');rng=np.random.default_rng(42);parts=[];filings=[];n=len(dates)
        for j,ticker in enumerate(['A','B']):
            p=pd.DataFrame({'date':dates,'session':np.arange(n),'ticker':ticker,'issuer':ticker,'weight':1.,'return_1':rng.normal(size=n),'target_end_1':pd.Series(dates).shift(-1)})
            for name in CONTROLS:p[name]=rng.normal(size=n)
            parts.append(p)
            for s in range(70,n,15):filings.append({'issuer':ticker,'accession':ticker+str(s),'session':s,'rows':[j*n+s],'categories':['a'],'text':'cash growth'})
        panel=pd.concat(parts,ignore_index=True);c={**config(),'fold_years':[2023],'horizons':[1],'inner_validation_fraction':.2,'validation_min_activations':2,'validation_min_issuers':2,
            'ridge_alphas':[1],'boosting_depths':[2],'boosting_iterations':2,'boosting_learning_rate':.05}
        # Actual exchange grids define offset arithmetic. Synthetic blocks here
        # use the same n rows, so provide their exact block length.
        with patch('discovery.atlas_features.sessions',return_value=dates):
            rows,trials,losses=forecast_cell(panel,filings,c,1,0,'return')
        global_losses=[x for x in losses if len(x['rows'])>100]
        self.assertGreaterEqual(len(global_losses),3)
        for x in global_losses[1:]:np.testing.assert_array_equal(x['rows'],global_losses[0]['rows'])
        self.assertTrue(all(panel.iloc[x['rows']].date.min()>=pd.Timestamp('2023-01-01') for x in losses))

    def test_missing_session_invalidates_long_outcome_and_no_2026(self):
        c=config();grid=sessions(c);rows=[]
        for ticker in ["A","B","SPY"]:
            for i,day in enumerate(grid):
                if ticker=="A" and i==100:continue
                rows.append({"ticker":ticker,"date":day,"close":100+i/100,"volume":1000})
        source={"settings":c,"mapping":{"A":{"cik":"1"},"B":{"cik":"1"}}}
        event={"issuer":"0000000001","accession":"f","category":"a","filing_date":"2022-01-07","tickers":["A","B"],"text":""}
        p,f,issues=build_panel(pd.DataFrame(rows),[event],source)
        self.assertTrue(np.isnan(p.iloc[99].return_2));self.assertTrue(np.isnan(p.iloc[len(grid)-1].return_1))
        self.assertEqual(f[0]["session"],5);self.assertEqual(p.iloc[0].weight,.5)
        self.assertTrue((p.date<=pd.Timestamp("2025-12-31")).all())

    def test_purge_uses_actual_target_end(self):
        from discovery.atlas_features import CONTROLS
        p=pd.DataFrame({"date":pd.to_datetime(["2022-12-29","2022-12-30","2023-01-03"]),"target_end_2":pd.to_datetime(["2022-12-30","2023-01-04","2023-01-05"]),"return_2":[.1,.1,.1]})
        for col in CONTROLS:p[col]=1.
        tr,va=outer_masks(p,2,2023,"return_2");self.assertEqual(tr.tolist(),[True,False,False]);self.assertEqual(va.tolist(),[False,False,True])

    def test_text_vocabulary_training_only_and_unknown_flag(self):
        t=TextFeatures(config()).fit(["cash growth","cash growth","cash growth"])
        self.assertNotIn("futuresecret",t.vectorizer.vocabulary_)
        a=t.transform(["futuresecret",""]);self.assertEqual(a[-1,-1],1);self.assertTrue(np.isfinite(a).all())

    def test_scramble_preserves_full_filing_bundles(self):
        c=config();f=[{"issuer":"i","accession":"x","session":10,"rows":[10],"categories":["a","b"],"text":"same"},
                      {"issuer":"i","accession":"y","session":20,"rows":[20],"categories":["c"],"text":"other"}]
        result=scramble(f,None,c,3);self.assertEqual(sorted(x["accession"] for x in result),["x","y"])
        self.assertTrue(all(x["session"]!=f[j]["session"] for j,x in enumerate(sorted(result,key=lambda x:x["accession"]))))
        self.assertEqual(next(x for x in result if x["accession"]=="x")["categories"],["a","b"])
        for x in result:self.assertEqual(x["rows"],[x["session"]]);self.assertIn("scramble_boundaries",x)

    def test_rw_matches_brute_force_and_controls_synthetic_null(self):
        rng=np.random.default_rng(42);draws=rng.normal(size=(999,6));obs=np.array([1,2,0,3,1,.5]);actual=romano_wolf(obs,draws)
        order=np.argsort(-abs(obs));expected=np.ones(6);last=0
        for step,i in enumerate(order):
            last=max(last,(1+(np.max(abs(draws[:,order[step:]]),axis=1)>=abs(obs[i])).sum())/1000);expected[i]=last
        np.testing.assert_allclose(actual,expected)
        false_positives=0
        for _ in range(200):
            null=rng.normal(size=6)
            false_positives+=bool((romano_wolf(null,draws)<.05).any())
        self.assertLessEqual(false_positives,20)

    def test_common_calendar_shocks_and_share_classes(self):
        w=joint_weights(np.array(["i","i","j","j"]),np.array([0,0,0,1]),1,np.random.default_rng(3));self.assertEqual(w[0],w[1]);self.assertTrue((w>=0).all())

    def test_pagination_cycle_preserved_as_incomplete(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"MASSIVE_API_KEY":"synthetic"}):
            store=Store(td)
            url="https://api.massive.com/test?limit=1"
            with patch.object(store,"_get",return_value={"results":[{"a":1}],"next_url":url}):
                with self.assertRaises(ValueError):store.pages("test","/test",{"limit":1})
            self.assertFalse(list((Path(td)/"objects").glob("*.json")));self.assertEqual(len(store.failures),1)
            with patch.object(store,"_get",side_effect=RequestBudget("limit")):
                with self.assertRaises(RequestBudget):store.pages("optional","/optional",{},optional=True)

    def test_redirect_denied_before_credentials(self):
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,302,"redirect",{},"https://example.com")

    def test_real_execution_requires_scheduler(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(RuntimeError):scheduled()

    def test_frozen_code_only_allowed_for_control_operations(self):
        import json
        from discovery import atlas
        from discovery.io import digest,identity
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';source=root/'source';run.mkdir();source.mkdir();(source/'source.json').write_text('{}')
            (root/'code.py').write_text('new');frozen=run/'frozen-code/code.py';frozen.parent.mkdir();frozen.write_text('old')
            m={'source':'source','source_sha256':digest(source/'source.json'),'code':{'code.py':digest(frozen)}};m['manifest_id']=identity(m);(run/'manifest.json').write_text(json.dumps(m))
            with patch.object(atlas,'ROOT',root):
                with self.assertRaises(ValueError):atlas.manifest(run)
                self.assertEqual(atlas.manifest(run,allow_frozen=True)['manifest_id'],m['manifest_id'])

    def test_pilot_job_scripts_and_return_integrity(self):
        import json,zipfile,hashlib
        from discovery import atlas_jobs
        from discovery.io import digest
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/"run";run.mkdir();(run/"manifest.json").write_text('{}')
            m={"manifest_id":"synthetic","settings":{"horizons":[1],"lags":[0],"resamples":9999,"resample_batch":100,"placebos":499}}
            with patch.object(atlas_jobs,"ROOT",root),patch.object(atlas_jobs,"manifest",return_value=m),patch.object(atlas_jobs,"remote_base",return_value=SYNTHETIC_REMOTE):
                atlas_jobs.jobs(run,SYNTHETIC_REMOTE+"/atlas-synthetic")
                body=(run/"hpg/pilot/submit.sh").read_text();self.assertIn("--dependency=afterok:$COVERAGE",body)
                self.assertIn("--array=0-3%4",(run/"hpg/pilot/pilot.sbatch").read_text())
                atlas_jobs.jobs(run,SYNTHETIC_REMOTE+"/atlas-synthetic",'uncertainty',32,16,inference_memory=128)
                self.assertIn('--mem=128gb',(run/'hpg/uncertainty/inference.sbatch').read_text())
                self.assertIn('--mem=16gb',(run/'hpg/uncertainty/resample.sbatch').read_text())
                archive=root/"return.zip";raw=b'evidence';receipt={"manifest_id":"synthetic","files":{"outputs/test.txt":hashlib.sha256(raw).hexdigest()}}
                with zipfile.ZipFile(archive,"w") as a:a.writestr("outputs/test.txt",raw);a.writestr("RETURN-RECEIPT.json",json.dumps(receipt))
                with self.assertRaises(ValueError):atlas_jobs.import_results(archive,run,"bad")
                self.assertEqual(atlas_jobs.import_results(archive,run,digest(archive))["verified_members"],1)
                with zipfile.ZipFile(archive,"w") as a:
                    receipt["files"]={"../outside.txt":hashlib.sha256(raw).hexdigest()};a.writestr("../outside.txt",raw);a.writestr("RETURN-RECEIPT.json",json.dumps(receipt))
                with self.assertRaises(ValueError):atlas_jobs.import_results(archive,run,digest(archive))

    def test_option_selection_uses_observed_spot_and_standard_contracts(self):
        from discovery.atlas_options import select,quote_mark
        c={**config(),"option_buckets":{"30":[21,45]},"option_otm_distance":.05,"option_otm_tolerance":.02}
        rows=[{"ticker":f"{side}{strike}","expiration_date":"2022-02-04","strike_price":strike,"contract_type":side,"shares_per_contract":100,"exercise_style":"american"} for strike in [95,100,105] for side in ["call","put"]]
        s=select(rows,{"date":"2022-01-03","stock_close":101},c)
        self.assertEqual(s["30"]["legs"]["atm_call"]["strike_price"],100)
        self.assertEqual(s["30"]["legs"]["otm_put"]["strike_price"],95)
        self.assertIsNone(quote_mark([{"sip_timestamp":1,"bid_price":2,"ask_price":1,"bid_size":1,"ask_size":1}],100))


if __name__=="__main__":unittest.main()
