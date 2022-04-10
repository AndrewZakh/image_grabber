from urllib.parse import urlparse
from urllib.parse import urljoin
import re
import argparse
import logging
import pathlib
import asyncio
import aiohttp
import aiofiles


class ImageGrabber():
    '''Main class.'''
    def __init__(self, url, path, auth=None):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)s'
                                   ' - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            filename='image_grabber.log',
                            filemode='a')
        self.logger = logging.getLogger('image_grabber')
        self.basic_auth = auth
        if self.basic_auth:
            self.aio_auth = aiohttp.BasicAuth(login=self.basic_auth[0],
                                              password=self.basic_auth[1])
        else:
            self.aio_auth = None
        self.url = url
        self.path = path
        self.addr_base = f'{urlparse(self.url).scheme}://'\
                         f'{urlparse(self.url).netloc}'

    def main(self):
        '''Main loop function.'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(ig.get_url_content())
        ig.parse_content()
        asyncio.run(self.download_all())

    def not_full_link(self, img_addr):
        '''This should be replaced with a better analyzer.'''
        if img_addr.find('://') == -1:
            return True
        else:
            return False

    async def get_url_content(self):
        '''Gets the html content from the url.'''
        async with aiohttp.ClientSession(auth=self.aio_auth) as session:
            async with session.get(self.url) as response:
                html = await response.text()
                self.body = html
                self.logger.debug(f'{self.body}')

    def parse_content(self):
        '''Parses the page to find PNG images using regex.'''
        # This code could be refactored with smth like BeautifulSoup library
        # but I was willing to show I can write regular expressions.
        rgx = re.compile(r'\<img[^>]{1,}src=[\"\']{1}([^\'\"]+.png)',
                         re.MULTILINE | re.IGNORECASE)
        matches = rgx.finditer(self.body)
        img_list = []
        for matchNum, match in enumerate(matches, start=1):
            if match.group(1) not in img_list:
                self.logger.debug(f'Adding {match.group(1)}')
                img_list.append(match.group(1))
        self.logger.info(f'Found {len(img_list)} objects')
        self.logger.debug(f'Images found: {img_list}')
        self.img_list = img_list

    async def download(self, img, session):
        '''Async downloads.'''
        self.logger.info(f'Downloading: {img}')
        filename = img.split('/')[-1:][0]
        self.logger.info(f'Saving file: {filename}')
        # Quickfix, should be replaced with a better analyzer
        if self.not_full_link(img):
            url = urljoin(self.addr_base, img)
            self.logger.debug(f'Downloading: {url}')
        else:
            url = img
        self.logger.debug(f'Downloading: {url}')
        full_path = pathlib.PurePath(self.path, filename)
        async with session.get(url) as response:
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(await response.read())

    async def download_all(self):
        '''Wrapper for async downloads.'''
        pathlib.Path(self.path).mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession(auth=self.aio_auth) as session:
            await asyncio.gather(
                *[self.download(img, session) for img in self.img_list]
            )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download PNG images from your URL.')
    parser.add_argument('--url', help='URL to process.')
    parser.add_argument('--path', help='Path to store files.')
    parser.add_argument('--username', help='Username in case of Basic Auth.')
    parser.add_argument('--password', help='Password in case of Basic Auth.')
    args = parser.parse_args()
    if args.username and args.password:
        ba = (args.username, args.password)
    else:
        ba = None
    ig = ImageGrabber(args.url, args.path, auth=ba)
    ig.main()
