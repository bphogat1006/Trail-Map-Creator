try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

# Custom open function (thread safe)
FILE_OPEN_LOCK = asyncio.Lock()
class OpenFileThreadSafe(object):
    def __init__(self, file, mode):
        self.file = file
        self.mode = mode
    async def __aenter__(self):
        await FILE_OPEN_LOCK.acquire()
        self.file = open(self.file, self.mode)
        return self.file
    async def __aexit__(self, *args):
        self.file.close()
        FILE_OPEN_LOCK.release()