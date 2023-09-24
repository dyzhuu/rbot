from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus
import re


def get_lyrics(unprocessed_song_name):
    try:
        song_name = re.sub(r'[^\w\s]', '', unprocessed_song_name)
        print(song_name)
        name = quote_plus(f"{song_name} site:genius.com")
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11'
               '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
               'Accept-Language': 'en-US,en;q=0.8',
               'Connection': 'keep-alive'}

        url = 'http://www.google.com/search?q=' + name

        print(url)

        result = requests.get(url, headers=hdr).text

        link_start = result.find('https://genius.com')

        if (link_start == -1):
            print('Lyric: link start not found')
            return

        link_end = result.find('&amp;', link_start + 1)

        url = result[link_start:link_end]

        print('Lyrics url:', url)

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
    except Exception as e:
        print("Lyrics error:", e)
