# Enter ESP32-S2 ROM download mode via CH340 DTR/RTS (this board needs IO0 held ~0.5s: slow EN rise)
import os,termios,fcntl,struct,time,sys
fd=os.open(sys.argv[1],os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
def setboth(dtr,rts):
    s=struct.unpack('I',fcntl.ioctl(fd,termios.TIOCMGET,struct.pack('I',0)))[0]
    s=(s|termios.TIOCM_DTR) if dtr else (s&~termios.TIOCM_DTR)
    s=(s|termios.TIOCM_RTS) if rts else (s&~termios.TIOCM_RTS)
    fcntl.ioctl(fd,termios.TIOCMSET,struct.pack('I',s))
setboth(False,True); time.sleep(0.2)
setboth(True,False); time.sleep(0.5)
setboth(False,False); time.sleep(0.1)
os.close(fd)
