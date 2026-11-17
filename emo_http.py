"""Bounded HTTP headers; one deadline per request, no per-byte timer tasks."""
import asyncio

class Buffered:
    """Bounded socket chunks; do not yield to I/O for each header byte."""
    def __init__(self,reader):self.reader=reader;self.pending=b'';self.offset=0
    async def read(self,n):
        if self.offset==len(self.pending):
            self.pending=await self.reader.read(128);self.offset=0
        end=min(len(self.pending),self.offset+n)
        data=self.pending[self.offset:end];self.offset=end
        return data
    async def readexactly(self,n):
        data=bytearray()
        while len(data)<n:
            part=await self.read(n-len(data))
            if not part:raise ValueError('short body')
            data.extend(part)
        return bytes(data)

async def _line(reader,limit):
    data=bytearray()
    while len(data)<=limit:
        c=await reader.read(1)
        if not c:raise ValueError('closed headers')
        data.extend(c)
        if data[-2:]==b'\r\n':return bytes(data[:-2])
    raise ValueError('header too long')
async def _request(reader):
    parts=(await _line(reader,128)).decode().split(' ')
    if len(parts)!=3:raise ValueError('request line')
    headers={};total=0
    for _ in range(20):
        raw=await _line(reader,512);total+=len(raw)
        if total>2048:raise ValueError('headers too large')
        if not raw:return parts[0],parts[1],headers
        name,value=raw.decode().split(':',1);name=name.lower().strip()
        if name in headers:raise ValueError('duplicate header')
        headers[name]=value.strip()
    raise ValueError('too many headers')
async def request(reader):return await asyncio.wait_for(_request(reader),5)
