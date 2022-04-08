import urllib3
from urllib.parse import urlparse
import re
import argparse
import logging
import pathlib
import asyncio
import aiohttp
import aiofiles


def not_full_link(img_addr):
    '''Dirty workaround'''
    if img_addr.find('://') == -1:
        return True
    else:
        return False

def get_url_content(url, auth=None):
    '''Gets the html content from the url.'''
    http = urllib3.PoolManager()
    if auth:
        # test basic auth & redirect
        headers = urllib3.make_headers(basic_auth=f'{auth[0]}:{auth[1]}')
        req = http.request('GET', url, headers=headers, redirect=True)
    else: 
        req = http.request('GET', url, redirect=True)
    charset_start = req.headers['Content-Type'].find('charset=')+8
    charset=req.headers['Content-Type'][charset_start:].lower()
    
    addr_base = f'{urlparse(req.geturl()).scheme}://{urlparse(req.geturl()).netloc}'
    html_body = req.data.decode(charset)
    return (addr_base, html_body)

def parse_content(addr_base, html_body):
    '''Parses the page to find PNG images.'''
    rgx = re.compile(r'\<img[^>]{1,}src=[\"\']{1}([^\'\"]+.png)', re.MULTILINE |re.IGNORECASE)
    # match = rgx.match(html_body)
    matches = rgx.finditer(html_body)
    img_list = []
    for matchNum, match in enumerate(matches, start=1):
        if match.group(1) not in img_list:
            logger.debug(f'Adding {match.group(1)}')
            img_list.append(match.group(1))
    logging.info(f'Found {len(img_list)} object')
    return img_list

def download_img(img, addr, path):
    '''Simple function without threads.'''
    logger.info(f'downloading: {img}')
    filename = img.split('/')[-1:][0]
    if not_full_link(img):
        url = f'{addr}{img}'
    else:
        url = img
    http = urllib3.PoolManager()
    r = http.request('GET', url, preload_content=False)
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(pathlib.PurePath(path, filename), 'wb') as out:
        while True:
            data = r.read(1024)
            if not data:
                break
            out.write(data)
    r.release_conn()
    return url

async def download(img, addr, path, session):
    '''Async downloads.'''
    logger.info(f'downloading: {img}')
    filename = img.split('/')[-1:][0]
    if not_full_link(img):
        url = f'{addr}{img}'
    else:
        url = img
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    full_path = pathlib.PurePath(path, filename)
    async with session.get(url) as response:
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(await response.read())

async def download_all(img_list, addr, path):
    '''Wrapper for async downloads.'''
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            *[download(img, addr, path, session) for img in img_list]
        )

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='image_grabber.log',
                    filemode='a')
logger = logging.getLogger('image_grabber')
parser = argparse.ArgumentParser(description='Download PNG images from your URL.')
parser.add_argument('--url', help='URL to process.')
parser.add_argument('--path', help='Path to store files.')
# parser.add_argument('--user', help='Username in case of Basic Auth.')
# parser.add_argument('--password', help='Password in case of Basic Auth.')
args = parser.parse_args()
addr, html = get_url_content(args.url)
img_list = parse_content(addr, html)
# for img in img_list:
    # download_img(img, addr, args.path)
    
asyncio.run(download_all(img_list, addr, args.path))
logger.info('Done.')