from asyncio import sleep
from dataclasses import dataclass
from datetime import datetime
from http.client import NOT_MODIFIED, OK
from logging import getLogger
from os import chmod, path, remove, scandir, stat, utime
from pathlib import PosixPath
from shutil import copy
from time import time
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from aiohttp import request

from judger2.config import cache_dir, cache_clear_interval_secs, \
                           cache_max_age_secs

logger = getLogger(__name__)


@dataclass
class CachedFile:
    path: PosixPath = None
    filename: str = None


def cached_from_url (url: str) -> CachedFile:
    cache = CachedFile()
    key = urlsplit(url).path
    cache_id = str(uuid5(NAMESPACE_URL, key))
    cache.path = PosixPath(path.join(cache_dir, cache_id))
    cache.filename = PosixPath(key).name
    return cache


utc_time_format = '%a, %d %b %Y %H:%M:%S GMT'


async def ensure_cached (url: str) -> CachedFile:
    cache = cached_from_url(url)
    headers = {}
    try:
        mtime = stat(cache.path).st_mtime
        date = datetime.fromtimestamp(mtime)
        utc_string = date.strftime(utc_time_format)
        headers['If-Modified-Since'] = utc_string
    except FileNotFoundError:
        mtime = time()
    async with request('GET', url, headers=headers) as resp:
        if resp.status == NOT_MODIFIED:
            utime(cache.path, (time(), mtime))
            return cache
        if resp.status != OK:
            raise Exception(f'Unknown response status {resp.status} while fetching object')
        with open(cache.path, 'w') as f:
            async for data, _ in resp.content.iter_chunks():
                f.write(data)
        last_modified = datetime \
            .strptime(resp.headers['Last-Modified'], utc_time_format) \
            .timestamp()
        utime(cache.path, (time(), last_modified))
        return cache


async def upload (local_path: str, url: str) -> CachedFile:
    cache = cached_from_url(url)
    copy(local_path, cache.path)
    chmod(cache.path, 0o640)
    utime(cache.path)
    with open(cache.path, 'rb') as f:
        async with request('PUT', url, data=f) as resp:
            if resp.status != OK:
                raise Exception(f'Unknown response status {resp.status} while uploading file')
    return cache


def clear_cache ():
    for file in scandir(cache_dir):
        if not file.is_file():
            continue
        st = file.stat()
        atime = max(st.st_atime, st.st_mtime)
        age = time() - atime
        if age > cache_max_age_secs:
            logger.debug(f'removing file {file.path} from cache as age is {age}')
            remove(file)

async def clean_cache_worker ():
    while True:
        try:
            logger.info('clearing cache')
            clear_cache()
        except Exception as e:
            logger.error(f'error while clearing cache: {e}')
        await sleep(cache_clear_interval_secs)
