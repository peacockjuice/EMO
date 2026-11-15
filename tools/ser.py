# tiny serial helper: reset board, optionally send text, print what comes back
import os,termios,fcntl,struct,time,select,sys
p=sys.argv[1]; send=sys.argv[2].encode().decode('unicode_escape').encode('latin1') if len(sys.argv)>2 else b''
fd=os.open(p,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
a=termios.tcgetattr(fd); a[0]=0;a[1]=0;a[3]=0;a[2]=termios.CS8|termios.CREAD|termios.CLOCAL; a[4]=a[5]=termios.B115200
termios.tcsetattr(fd,termios.TCSANOW,a)
def setboth(dtr,rts):
    s=struct.unpack('I',fcntl.ioctl(fd,termios.TIOCMGET,struct.pack('I',0)))[0]
    s=(s|termios.TIOCM_DTR) if dtr else (s&~termios.TIOCM_DTR)
    s=(s|termios.TIOCM_RTS) if rts else (s&~termios.TIOCM_RTS)
    fcntl.ioctl(fd,termios.TIOCMSET,struct.pack('I',s))
def rd(t):
    buf=b''; e=time.time()+t
    while time.time()<e:
        r,_,_=select.select([fd],[],[],0.05)
        if r:
            try: buf+=os.read(fd,4096)
            except BlockingIOError: pass
    return buf
setboth(False,True); time.sleep(0.2); setboth(False,False)
out=rd(3.0)
if send:
    os.write(fd,send); out+=rd(2.0)
os.close(fd)
sys.stdout.write(out.decode('latin1'))
