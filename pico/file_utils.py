try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

# Custom context manager wrapper for open, allows only one file to be open at a time
FILE_OPEN_LOCK = asyncio.Lock()
class OpenFileSafely(object):
    def __init__(self, file, mode='r'):
        self.file = file
        self.mode = mode
    async def __aenter__(self):
        await FILE_OPEN_LOCK.acquire()
        self.file = open(self.file, self.mode)
        return self.file
    async def __aexit__(self, *args):
        self.file.close()
        FILE_OPEN_LOCK.release()

# Reads track CSV's in small chunks as to not interrupt asyncio for too long
class TrackReader:
    def __init__(self, filename):
        self.__filename = filename
        self.__file = None
        self.__lat_col = None
        self.__long_col = None
        self.__curr_seek_pos = None
        self.__counter = 1
        self.__CHUNK_SIZE = 20
        self.__initialized = False

    async def read_header(self):
        # figure out which columns are which
        async with OpenFileSafely(f'tracks/{self.__filename}') as f:
            header = f.readline()
            cols = header.split(',')
            for i,col in enumerate(cols):
                if 'latitude' in col:
                    self.__lat_col = i
                elif 'longitude' in col:
                    self.__long_col = i
            if self.__lat_col is None or self.__long_col is None:
                raise Exception('Unable to parse CSV file:', self.__filename)
            # set seek position to start reading at
            self.__curr_seek_pos = f.tell()

    async def __open_file(self):
        await FILE_OPEN_LOCK.acquire()
        self.__file = open(f'tracks/{self.__filename}')
        self.__file.seek(self.__curr_seek_pos)

    def __close_file(self):
        self.__file.close()
        self.__file = None
        FILE_OPEN_LOCK.release()

    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.__initialized:
            await self.read_header()
            # class is now initialized
            self.__initialized = True

        if self.__file is None:
            await self.__open_file()

        line = self.__file.readline()
        if not line or line.strip() == '':
            self.__close_file()
            raise StopAsyncIteration

        parts = line.split(',')
        lat = float(parts[self.__lat_col])
        long = float(parts[self.__long_col])

        if self.__counter % self.__CHUNK_SIZE == 0:
            # set new seek position
            self.__curr_seek_pos = self.__file.tell()
            
            # close file
            self.__close_file()

            # allow asyncio to execute other code in event loop
            await asyncio.sleep(0)

        self.__counter += 1
        return lat, long

# Does a file exist? (os.access() not implemented in upython)
async def file_exists(file):
    try:
        await FILE_OPEN_LOCK.acquire()
        with open(file, 'r'):
            return True
    except OSError:
        return False
    finally:
        FILE_OPEN_LOCK.release()