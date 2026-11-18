"""Observe a real unread reply through a minute reminder; does not change BB state."""
import argparse,datetime,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def status():return json.loads(subprocess.check_output(['bb','emo','status']))
def run(report_path,seconds):
    report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':False,'samples':[]}
    try:
        initial=status()
        target=next((s for s in initial['threads'] if not s['excluded'] and s['kind']=='done' and s['completion']),None)
        if target is None:raise RuntimeError('No unread reply available; this check creates no synthetic user messages')
        report['alias']=target['alias'];report['completion']=target['completion']
        deadline=time.monotonic()+seconds
        while True:
            snapshot=status();row=next((s for s in snapshot['threads'] if s['id']==target['id']),None)
            report['last_observation']={'sourceReady':snapshot['sourceReady'],'delivery':snapshot['delivery'],'error':snapshot['error'],'completion':row['completion'] if row else None,'excluded':row['excluded'] if row else None}
            assert row and not row['excluded'] and row['completion']==target['completion'],'Target was read, excluded or superseded during observation'
            assert snapshot['sourceReady'] and snapshot['delivery']=='live','Source or delivery is not live'
            report['samples'].append({'at':int(time.time()*1000),'kind':row['kind'],'completion':row['completion'],'notifiedAt':row.get('notifiedAt'),'notifiedCompletion':row.get('notifiedCompletion'),'receipt':snapshot['receipt']})
            if time.monotonic()>=deadline:break
            time.sleep(5)
        notices=sorted({s['notifiedAt'] for s in report['samples'] if s['notifiedAt'] is not None})
        assert len(notices)>=2,'No repeated reminder observed'
        assert all(b-a>=60000 for a,b in zip(notices,notices[1:])),'Reminder repeated too soon'
        assert all(s['kind']=='done' for s in report['samples']),'Display changed unread classification'
        report['passed']=True
        print('PASS unread reply survives display and repeats after at least 60 seconds:',target['alias'])
    except Exception as e:
        report['error']=type(e).__name__+': '+str(e);raise
    finally:
        report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        report_path.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seconds',type=int,default=75);p.add_argument('--report',type=Path,default=ROOT/'preview/bb-attention-reminders.json');a=p.parse_args()
    if a.seconds<65:p.error('Observe for at least 65 seconds')
    run(a.report,a.seconds)
