from sim_r5 import run
import statistics
for model in ['tick','op']:
    for resend in ['range']:
        row=[]
        for kb in (20,25,30,35,40,52,100,300):
            L=[];H=[];n=0
            for s in range(60):
                r = run(kb*1024, collector_start=40, dur=1800, fail=model, step_rule='rev', seed=s, resend=resend)
                L.append(r['lost_s']); H.append(r['max_hold'])
                n += r['lost_s']>0.05
            row.append(f"{kb}:{statistics.mean(L):.1f}s {n}/60 h{max(H):.0f}")
        print(model, resend, ' | '.join(row), flush=True)
