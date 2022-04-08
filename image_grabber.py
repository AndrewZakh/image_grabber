from urllib.parse import urlparse, urljoin
import re
import argparse
import logging
import pathlib
import asyncio
import aiohttp
import aiofiles

class ImageGrabber():
    def __init__(self, url, path='./images', auth=None):
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='image_grabber.log',
                    filemode='a')
        self.logger = logging.getLogger('image_grabber')
        self.basic_auth = auth
        self.aio_auth = aiohttp.BasicAuth(login = self.basic_auth[0], 
                                          password = self.basic_auth[1])
        self.url = url
        self.path = path
        self.addr_base = f'{urlparse(self.url).scheme}://'\
                         f'{urlparse(self.url).netloc}'


    def not_full_link(self, img_addr):
        '''Dirty workaround'''
        if img_addr.find('://') == -1:
            return True
        else:
            return False

    async def get_url_content(self):
            '''Gets the html content from the url.'''
            if self.basic_auth:
                aio_auth = aiohttp.BasicAuth(login = self.basic_auth[0], 
                                             password = self.basic_auth[1])
            async with aiohttp.ClientSession(auth=aio_auth) as session:
                async with session.get(self.url) as response:
                    html = await response.text()
                    self.body = html
                    self.logger.debug(f'{self.body}')

    def parse_content(self):
        '''Parses the page to find PNG images using regex.'''
        rgx = re.compile(r'\<img[^>]{1,}src=[\"\']{1}([^\'\"]+.png)', re.MULTILINE |re.IGNORECASE)
        matches = rgx.finditer(self.body)
        img_list = []
        for matchNum, match in enumerate(matches, start=1):
            if match.group(1) not in img_list:
                self.logger.debug(f'Adding {match.group(1)}')
                img_list.append(match.group(1))
        self.logger.info(f'Found {len(img_list)} objects')
        self.img_list = img_list

    async def download(self, img, session):
        '''Async downloads.'''
        self.logger.info(f'downloading: {img}')
        filename = img.split('/')[-1:][0]
        self.logger.info(f'Saving file: {filename}')
        if not_full_link(img):
            if img[0] != '/':
                img = f'/{img}'
            url = f'{self.addr_base}{img}'
            self.logger.debug(f'Downloading: {url}')
        else:
            url = img
        self.logger.debug(f'Downloading: {url}')
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        full_path = pathlib.PurePath(path, filename)
        async with session.get(url) as response:
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(await response.read())

    async def download_all(img_list, addr, path, auth=None):
        '''Wrapper for async downloads.'''
        if auth!=None:
            basic_auth = aiohttp.BasicAuth(login=auth[0], password=auth[0], encoding='utf-8')
            aiohttp_session = aiohttp.ClientSession(auth=basic_auth)
        else:
            aiohttp_session = aiohttp.ClientSession()
        async with aiohttp_session as session:
            await asyncio.gather(
                *[download(img, addr, path, session, auth) for img in img_list]
            )

    def main(self):
        # asyncio.run(ig.get_url_content())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(ig.get_url_content())
        ig.parse_content()
        asyncio.run(download_all())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download PNG images from your URL.')
    parser.add_argument('--url', help='URL to process.')
    parser.add_argument('--path', help='Path to store files.')
    parser.add_argument('--username', help='Username in case of Basic Auth.')
    parser.add_argument('--password', help='Password in case of Basic Auth.')
    args = parser.parse_args()
    if args.username and args.password:
        ba = (args.username, args.password)
    else:
        ba = None
    ig = ImageGrabber(args.url, path=args.path, auth=ba)
    ig.main()
    
    
    
