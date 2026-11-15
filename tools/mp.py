# minimal MicroPython raw-REPL client over a UART bridge (no board reset on open)
import os,termios,fcntl,struct,time,select,sys
def opn(p):
    fd=os.open(p,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
    a=termios.tcgetattr(fd); a[0]=0;a[1]=0;a[3]=0;a[2]=termios.CS8|termios.CREAD|termios.CLOCAL; a[4]=a[5]=termios.B115200
    termios.tcsetattr(fd,termios.TCSANOW,a)
    s=struct.unpack('I',fcntl.ioctl(fd,termios.TIOCMGET,struct.pack('I',0)))[0]
    fcntl.ioctl(fd,termios.TIOCMSET,struct.pack('I',s&~termios.TIOCM_DTR&~termios.TIOCM_RTS))
    return fd
def rd(fd,t,until=None):
    buf=b''; e=time.time()+t
    while time.time()<e:
        r,_,_=select.select([fd],[],[],0.02)
        if r:
            try: buf+=os.read(fd,4096)
            except BlockingIOError: pass
            if until and until in buf: break
    return buf
def wr(fd,b):
    for i in range(0,len(b),64):
        os.write(fd,b[i:i+64]); time.sleep(0.01)
def raw(fd):
    wr(fd,b'\r\x03\x03'); rd(fd,0.5); wr(fd,b'\x01'); r=rd(fd,1.5,b'raw REPL')
    if b'raw REPL' not in r: raise SystemExit('no raw REPL: %r'%r[-200:])
    rd(fd,0.2)
def ex(fd,code,t=10):
    wr(fd,code.encode()+b'\x04'); r=rd(fd,t,b'\x04>')
    if not r.startswith(b'OK'): raise SystemExit('exec failed: %r'%r[:300])
    out,err=r[2:].split(b'\x04')[:2]
    if err.strip(): raise SystemExit('board error: '+err.decode())
    return out.decode()
if __name__=='__main__':
    port,cmd=sys.argv[1],sys.argv[2]
    fd=opn(port); time.sleep(0.3); raw(fd)
    if cmd=='put':
        for path in sys.argv[3:]:
            data=open(path,'rb').read(); name=os.path.basename(path)
            ex(fd,"f=open(%r,'wb')"%name)
            for i in range(0,len(data),128): ex(fd,"f.write(%r)"%data[i:i+128])
            ex(fd,"f.close()")
            print(name, ex(fd,"import os;print(os.stat(%r)[6])"%name).strip(),'bytes on board, local',len(data))
    elif cmd=='exec':
        print(ex(fd,sys.argv[3],float(sys.argv[4]) if len(sys.argv)>4 else 10),end='')
    wr(fd,b'\x02'); os.close(fd)
