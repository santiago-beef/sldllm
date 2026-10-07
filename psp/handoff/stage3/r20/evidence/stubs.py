import struct,sys
d=open('DATA.PSP','rb').read()
VA0=0x08900018; FO0=0x1018
def u32(va): return struct.unpack('<I',d[FO0+va-VA0:FO0+va-VA0+4])[0]
def cstr(va):
    o=FO0+va-VA0; e=d.index(b'\0',o); return d[o:e].decode()
# known NIDs (from public PSP SDK NID lists; identities UNVERIFIED unless confirmed by usage)
known={
0x109F50BC:'sceIoOpen',0x6A638D83:'sceIoRead',0x810C4BC3:'sceIoClose',0x27EB27B8:'sceIoLseek',
0x42EC03AC:'sceIoWrite',0xACE946E8:'sceIoGetstat',0x55F4717D:'sceIoChdir',0x68963324:'sceIoLseek32',
0x237DBD4F:'sceKernelAllocPartitionMemory',0x9D9A5BA1:'sceKernelGetBlockHeadAddr',0xB6D61D02:'sceKernelFreePartitionMemory',
0xA291F107:'sceKernelMaxFreeMemSize',0xF919F628:'sceKernelTotalFreeMemSize',0x3FC9AE6A:'sceKernelDevkitVersion',
0x05572A5F:'sceKernelExitGame',0x4AC57943:'sceKernelRegisterExitCallback',0xBD2F1094:'sceKernelLoadExec',
0xE81CAF8F:'sceKernelCreateCallback',0x82826F70:'sceKernelSleepThreadCB',0x446D8DE6:'sceKernelCreateThread',
0xF475845D:'sceKernelStartThread',0xAA73C935:'sceKernelExitThread',0x809CE29B:'sceKernelExitDeleteThread',
0xCEADEB47:'sceKernelDelayThread',0x293B45B8:'sceKernelGetThreadId',0x9ACE131E:'sceKernelSleepThread',
0x977DE386:'sceKernelLoadModule',0x50F0C1EC:'sceKernelStartModule',0xD1FF982A:'sceKernelStopModule',
0x2E0911AA:'sceKernelUnloadModule',0xD675EBB8:'sceKernelSelfStopUnloadModule',0xD8B73127:'sceKernelGetModuleIdByAddress',
0x0E20F177:'sceDisplaySetMode',0x289D82FE:'sceDisplaySetFrameBuf',0x984C27E7:'sceDisplayWaitVblankStart',
0xEEDA2E54:'sceDisplayGetFrameBuf',0xDEA197D4:'sceDisplayGetMode',
0x3054D478:'sceKernelStdin',0x172D316E:'sceKernelStdout',0xA6AA1C29:'sceKernelStderr',
0x27CC57F0:'sceKernelLibcTime',0x91E4F6A7:'sceKernelLibcClock',0x71EC4271:'sceKernelLibcGettimeofday',
0x79D1C3FA:'sceKernelDcacheWritebackAll',0xB435DEC5:'sceKernelDcacheWritebackInvalidateAll',
0x3EE30821:'sceKernelDcacheWritebackRange',0x34B9FA9E:'sceKernelDcacheWritebackInvalidateRange',
0xB4F78E95:'sceGeEdramGetAddr',0xE47E40E4:'sceGeEdramGetAddr?',0x1F6752AD:'sceGeEdramGetSize',
0x17943399:'sceNetInetInit',0xA9ED66B9:'sceNetInetTerm',
0xB2D5BD4F:'sceKernelCreateSema?',0xD6DA4BA1:'sceKernelCreateSema',0x28B6489C:'sceKernelDeleteSema',
0x3F53E640:'sceKernelSignalSema',0x4E3A1105:'sceKernelWaitSema',0x6D212BAC:'sceKernelWaitSemaCB',
0xB29DDF9C:'sceIoDopen',0xE3EB004C:'sceIoDread',0xEB092469:'sceIoDclose',0x06A70004:'sceIoMkdir',
0x1117C65F:'sceIoRmdir',0xF27A9C51:'sceIoRemove',0x779103A0:'sceIoRename',0xB8A740F4:'sceIoChstat',
0x63632449:'sceIoIoctl',0x54F5FB11:'sceIoDevctl',0xA905B705:'sceIoCloseAll',0x3251EA56:'sceIoPollAsync',
0xE23EEC33:'sceKernelWaitThreadEnd',0x9FA03CD3:'sceKernelDeleteThread',0x616403BA:'sceKernelTerminateThread',
0x383F7BCC:'sceKernelTerminateDeleteThread',0x0C106E53:'sceKernelRegisterThreadEventHandler',
0x17C1684E:'sceKernelReferThreadStatus',0x94AA61EE:'sceKernelGetThreadCurrentPriority',
0x369ED59D:'sceKernelGetSystemTimeLow',0xDB738F35:'sceKernelGetSystemTime',0x82BC5777:'sceKernelGetSystemTimeWide',
0x110DEC9A:'sceKernelUSec2SysClock',0xBA6B92E2:'sceKernelSysClock2USec',
0xD13BDE95:'sceKernelCheckThreadStack',0x7C0DC2A0:'sceKernelCreateMsgPipe',
0x4AA7F3B0:'?',0xFC114573:'sceKernelGetCompiledSdkVersion?',0x7591C7DB:'sceKernelSetCompiledSdkVersion',
0x13A5ABEF:'sceKernelPrintf?',
}
o=FO0+0x08920a1c-VA0
res={}
for i in range(0xc8//20):
    name,ver,attr,elen,vc,fc,nidtab,stubtab=struct.unpack('<IHHBBHII',d[o+20*i:o+20*i+20])
    lib=cstr(name)
    for k in range(fc):
        nid=u32(nidtab+4*k); st=stubtab+8*k
        res[st]=(lib,nid,known.get(nid,'?'))
for st in sorted(res):
    lib,nid,nm=res[st]
    print('%#010x %-18s %#010x %s'%(st,lib,nid,nm))
