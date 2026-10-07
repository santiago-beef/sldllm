import struct, math
# ---- formats (10.3, r5) ----
F = {
 'SC':   '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH',
 'WEXT': '<5I16I5IBBBB4I4I16IHH',
 'POLL': '<IIIIH7B2b5BHHBBBB',
 'S':    '<IIIIIHHBBHBBHII',
 'STATS':'<192I',
 'CTL':  '<I7I',
 'CHUNK':'<4sHHIII',
 'BLOCK':'<BBHI',
 'FILEHDR':'<8sIIIIIIIII',
 'UHB':  '<21I',
}
for k,v in F.items(): print(f"{k:8s} {struct.calcsize(v)}")
SC=struct.calcsize(F['SC']); W=SC+struct.calcsize(F['WEXT']); PO=struct.calcsize(F['POLL']); S=struct.calcsize(F['S'])
# SC offsets
names='seq tick_in c_in c_out dtick cmd txlen ret nwords retries ack_polls drain drain_last gpio_in spi_st9 spi_sttx ctx wn w_head_lo pre_wrk pre_cls ms_delta pre_flags preempt_delta rx lc_epc lc_dtick lc_n lc_flags led_or led_pid pre_tot'.split()
off=0; fmt=F['SC'][1:]; i=0; out=[]
import re
for tok in re.findall(r'\d*[A-Za-z]', fmt):
    n = int(tok[:-1]) if len(tok)>1 else 1; c=tok[-1]
    if c=='s': out.append((names[i],off)); off+=n; i+=1
    else:
        for _ in range(n): out.append((names[i],off)); off+=struct.calcsize('<'+c); i+=1
print('SC offsets', out)
UHBW='tickno stats_now_tick gtod_sec gtod_usec uptime_cs memfree_kb mouse_pkts_total mouse_press_total bytes_synced_total last_write_ms last_fsync_ms max_fsync_ms_60s max_tick_ms_60s write_errs last_errno flags durable_tick lag_max seg drain_stuck nonce'.split()
print('UHB words', len(UHBW), [(n,4*i) for i,n in enumerate(UHBW)][-3:])
FH='magic fmt run seg inst wpid spid now_tick now_jiffies nonce'.split()
print('FILEHDR fixed', struct.calcsize(F['FILEHDR']), 'payload', struct.calcsize(F['FILEHDR'])+768+256)
# ---- rates ----
polls=250/14; P=2*polls; Wr=250/1250
tick=0.23; tps=1/tick
uhb_chunk=20+struct.calcsize(F['UHB'])
Sflush=22.6
rates={'P':P*SC,'POLL':polls*PO,'W':Wr*W,'S':Sflush*S,'RECS hdr':tps*(20+5*8),'UHB':tps*uhb_chunk,'STATS':tps/8*(20+768),'PROCS':tps/40*1156,'PAD hdr':tps*20}
for k,v in rates.items(): print(f"  {k:9s} {v:8.1f}")
payload=sum(rates.values()); print('steady payload B/s', round(payload))
nom=(payload-rates['STATS']-rates['PROCS'])/tps
print('flush nominal/+STATS/+STATS+PROCS', round(nom), round(nom+788), round(nom+788+1156))
pad=lambda b:max(1536,(int(math.ceil(b))+511)//512*512)
sz=[pad(nom)]*35+[pad(nom+788)]*4+[pad(nom+788+1156)]
avg=sum(sz)/40; print('padded avg per tick', avg, 'sectors', avg/512, 'on-stick B/s', round(avg*tps))
# creation ticks: flush S 27.0/s, creation S 11.5/step
cnom=nom+(27.0-Sflush)*S/tps+11.5*S
csz=[pad(cnom)]*35+[pad(cnom+788)]*4+[pad(cnom+788+1156)]
cavg=sum(csz)/40; print('creation tick flush', round(cnom), 'sectors', cavg/512, 'on-stick B/s', round(cavg*tps))
SEG=2097152; life=None
on=avg*tps; frac=None
# life of a 2 MB file at average rate; creation ticks: 256 steps
ticks_per_file=(SEG-1536)/((avg*0.787+cavg*0.213))
frac=256/ticks_per_file
oavg=(1-frac)*avg+frac*cavg
print('frac creation ticks', round(frac,3), 'run avg on-stick B/s', round(oavg*tps), 'file life s', round(ticks_per_file*tick))
pay_avg=payload+frac*((27.0-Sflush)*S+11.5*S*tps)
print('run avg payload', round(pay_avg))
for mins in (15,30,35): print(mins,'min MB', round(oavg*tps*60*mins/1e6,2), 'files', math.ceil(oavg*tps*60*mins/(SEG-1536)))
# creation physical
cw=4096+256*2+64*2   # data + (dir+FSINFO) per 8 KB step + one FAT sector in two copies per 32 KB cluster
print('creation sector writes per file', cw, 'per s', round(cw/(ticks_per_file*tick),1), 'KB/s', round(cw*512/(ticks_per_file*tick)/1024,2))
sw=(avg/512+2)*tps*(1-frac)+(cavg/512+2)*tps*frac
print('flush sector writes/s', round(sw,1), 'total', round(sw+cw/(ticks_per_file*tick),1))
# rings
rings={'P':4096*SC,'POLL':2048*PO,'W':256*W,'S':4096*S,'M':64*SC}
print('rings', sum(rings.values()), {k:v for k,v in rings.items()})
print('spans P', 4096/P, 'W', 256/Wr, 'S steady', 4096/Sflush, '8KB', 4096/77, '64KB', 4096/144)
cap=48*SC+24*PO+2*W+64*S+8*SC; print('per cap', cap, 'RECS max', 4*cap+40+20, 'flush max', 4*cap+60+788+2420+uhb_chunk+20)
