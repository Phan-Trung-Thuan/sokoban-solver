import os,sys,time,json
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,ROOT);os.chdir(ROOT)
from main import parse_xsb_file
from solver import SokobanSolver
levels=parse_xsb_file('assets/levels/microban_155.xsb')[:60]
cfgs=[('BFS','MONODIRECTIONAL'),('DFS','MONODIRECTIONAL'),('IDS','MONODIRECTIONAL'),('GREEDY','MONODIRECTIONAL'),('A*','MONODIRECTIONAL'),('BFS','BIDIRECTIONAL'),('A*','BIDIRECTIONAL')]
LIM,TL=1_000_000,60.0
import pathlib
done=set()
if pathlib.Path(sys.argv[1]).exists():
  for l in open(sys.argv[1]):
    j=json.loads(l);done.add((j['alg'],j['dir'],j['lvl']))
out=open(sys.argv[1],'a')
T0=time.perf_counter()
for alg,dr in cfgs:
  for i,lv in enumerate(levels,1):
    if (alg,dr,i) in done: continue
    if time.perf_counter()-T0>100: sys.exit(0)
    s=SokobanSolver(lv,alg,dr);t0=time.perf_counter();st='TIMEOUT';path=None
    while True:
      r,v=s.step()
      if r=='SOLVED': st='SOLVED';path=v;break
      if r=='FINISHED': st='NOSOL';break
      if s.steps_explored>=LIM: st='LIMIT';break
      if time.perf_counter()-t0>TL: st='TIMEOUT';break
    dt=time.perf_counter()-t0
    out.write(json.dumps(dict(alg=alg,dir=dr,lvl=i,status=st,states=s.steps_explored,steps=len(s.solution_actions) if st=='SOLVED' else None,time=round(dt,3)))+'\n');out.flush()
