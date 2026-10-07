from sim_r5 import run
for rule in ['r4','rev','need']:
    print('rule', rule)
    for cs in (20.0, 40.0):
        row=[]
        for kb in (20,25,30,35,40,52,100,300):
            r = run(kb*1024, collector_start=cs, dur=600, step_rule=rule)
            row.append(f"{kb}:{r['first_flush']:.1f}/{(r['first_complete'] or -1):.0f}/L{r['lost_s']:.0f}")
        print(' start',cs, '  '.join(row))
