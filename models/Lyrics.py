import re
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from typing import List
from .Exceptions import LyricNotFoundException


class Lyrics:
    def __init__(self, search: str):
        self.url = None
        self.lyrics = []

    def get_genius_lyrics(self, song_name: str) -> List[str]:  # genius
        song_name = re.sub(r"\([^()]*\)", "", song_name)
        song_name = re.sub(r'[^\w\s]', ' ', song_name)
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11'
               '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
               'Accept-Language': 'en-US,en;q=0.8',
               'Connection': 'keep-alive'}
        name = quote_plus(f"{song_name} site:genius.com")
        url = 'http://www.google.com/search?q=' + name

        result = requests.get(url, headers=hdr).text

        link_start = result.find('https://genius.com')

        if (link_start == -1):
            raise LyricNotFoundException('Link start not found')
        link_end = result.find('&amp;', link_start + 1)

        self.url = result[link_start:link_end]

        song_html = requests.get(url).content
        soup = BeautifulSoup(song_html, 'lxml')

        for tag in soup.select('div[class^="Lyrics__Container"], .song_body-lyrics p'):
            t = tag.get_text(strip=True, separator='\n')
            t = t.replace('(\n', '(') \
                .replace('\n)', ')') \
                .replace('\n]', ']') \
                .replace('[\n', '[') \
                .replace('\n,', ',') \
                .replace(',\n', ', ')
            if t:
                self.lyrics.append(t)
