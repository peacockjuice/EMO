"""Verify full panel transfers alongside live BB delivery; no credentials in output."""
import argparse,datetime,hashlib,json,subprocess,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def bridge():
    value=json.loads(subprocess.check_output(['bb','emo','status']))
    return {k:value[k] for k in ('sourceReady','delivery','receipt')}
def run(url,rounds,interval,report_path):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    expected=(ROOT/'index.html').read_bytes()
    report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':url,'passed':False,'samples':[]}
    try:
        for n in range(rounds):
            sample={};report['samples'].append(sample)
            start=time.monotonic()
            with opener.open(url+'/',timeout=12) as response:
                body=response.read(len(expected)+1)
                sample['content_length']=response.headers.get('Content-Length')
            sample['html_seconds']=round(time.monotonic()-start,3)
            sample['html_bytes']=len(body)
            assert sample['content_length']==str(len(expected)),'Missing or incorrect Content-Length'
            assert body==expected,'Served panel differs from local build or was truncated'
            sample['html_sha256']=hashlib.sha256(body).hexdigest()
            with opener.open(url+'/state',timeout=6) as response:sample['device']=json.loads(response.read(2048))
            sample['bridge']=bridge()
            assert sample['device']['mood']=='bb' and sample['device']['bb']=='live','Device BB mode is not live'
            assert sample['bridge']['sourceReady'] and sample['bridge']['delivery']=='live','Bridge does not confirm live delivery'
            print('PASS panel + live snapshot',n+1,'/',rounds,flush=True)
            if n+1<rounds:time.sleep(interval)
        first,last=report['samples'][0],report['samples'][-1]
        assert last['bridge']['receipt']['epoch']==first['bridge']['receipt']['epoch'],'Bridge restarted during check'
        assert last['bridge']['receipt']['seq']>first['bridge']['receipt']['seq'],'No new acknowledged snapshots'
        assert last['device']['frames']>first['device']['frames'],'No rendered frame progress'
        report['passed']=True
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        report_path.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://192.168.1.43');p.add_argument('--rounds',type=int,default=6);p.add_argument('--interval',type=float,default=10);p.add_argument('--report',type=Path,default=ROOT/'preview/bb-acceptance.json');args=p.parse_args()
    if args.rounds<2 or args.interval<1:p.error('Use at least two rounds and an interval of at least one second')
    run(args.url.rstrip('/'),args.rounds,args.interval,args.report)
