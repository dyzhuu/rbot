from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus


def get_lyrics(song_name):
    song_name += ' site:genius.com'
    name = quote_plus(song_name)
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11'
           '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}

    url = 'http://www.google.com/search?q=' + name

    result = requests.get(url, headers=hdr).text

    link_start = result.find('https://genius.com')

    if (link_start == -1):
        return

    link_end = result.find('&amp;', link_start + 1)
    url = result[link_start:link_end]

    soup = BeautifulSoup(requests.get(url).content, 'lxml')

    lyrics = []
    for tag in soup.select('div[class^="Lyrics__Container"], .song_body-lyrics p'):
        t = tag.get_text(strip=True, separator='\n')
        t = t.replace('(\n', '(')
        t = t.replace('\n)', ')')
        t = t.replace('\n]', ']')
        t = t.replace('[\n', '[')
        t = t.replace('\n,', ',')
        t = t.replace(',\n', ', ')
        if t:
            lyrics.append(t)

    return lyrics
