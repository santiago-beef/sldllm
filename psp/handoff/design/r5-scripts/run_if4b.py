from sim_r5 import run
import statistics
for kb in (22,25,28,30,35):
    for model in ('tick','op'):
        L=[];H=[];n=0
        for s in range(200):
            r = run(kb*1024, collector_start=40, dur=1800, fail=model, step_rule='rev', seed=1000+s)
            L.append(r['lost_s']); H.append(r['max_hold']); n += r['lost_s']>0.05
        print(kb, model, f"mean {statistics.mean(L):.2f}s runs-with-loss {n}/200 maxhold {max(H):.0f}s", flush=True)
