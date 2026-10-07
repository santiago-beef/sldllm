from sim_r5 import run
for kb in (25,30,52,100,300):
    row=[]
    for B in (35,60,90,100,110,130):
        worst=0; wh=0
        for b0 in range(45, 1500, 37):
            r = run(kb*1024, collector_start=40, dur=1800, fail='burst', burst=(40+b0,B), step_rule='rev')
            worst=max(worst,r['lost_s']); wh=max(wh,r['max_hold'])
        row.append(f"B{B}: L{worst:.0f} h{wh:.0f}")
    print(kb, ' | '.join(row), flush=True)
