from sim_r5 import run
for kb in (25,35,52,100,300):
    row=[]
    for R in (768*1024, 1536*1024, 2*1024*1024):
        for esc in (False, True):
            # region inside file 2 starting 64 KB in, goes bad at t=60 s after start (file 2 created by then)
            r = run(kb*1024, collector_start=40, dur=1200, step_rule='rev', if9=(2, 65536, 65536+R, 40+60), escape=esc)
            row.append(f"R{R//1024}K {'esc' if esc else 'r4 '}: L{r['lost_s']:.0f} h{r['max_hold']:.0f}")
    print(kb, ' | '.join(row), flush=True)
