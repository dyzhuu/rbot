from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus
import re
from dotenv import load_dotenv

load_dotenv()


def split_lyric(lyric):
    if len(lyric) > 1000:
        lines = lyric.split('\n')
        middle_index = len(lines) // 2

        first_part = ['\n'.join(lines[:middle_index])]
        second_part = ['\n'.join(lines[middle_index:])]

        first_part = split_lyric(first_part[0])
        second_part = split_lyric(second_part[0])

        return [*first_part, *second_part]
    return [lyric]


def get_lyrics(song_name):  # genius
    try:
        song_name = re.sub(r"\([^()]*\)", "", song_name)
        song_name = re.sub(r'[^\w\s]', ' ', song_name)

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

        song_html = requests.get(url).content

        soup = BeautifulSoup(song_html, 'lxml')

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


def get_lyrics1(song_name):  # letras
    try:
        song_name = re.sub(r"\([^()]*\)", "", song_name)
        song_name = re.sub(r'[^\w\s]', ' ', song_name)

        name = quote_plus(f"{song_name} site:letras.com")
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11'
               '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
               'Accept-Language': 'en-US,en;q=0.8',
               'Connection': 'keep-alive'}

        url = 'http://www.google.com/search?q=' + name

        print(url)

        result = requests.get(url, headers=hdr).text

        link_start = result.find('https://www.letras.com')

        if (link_start == -1):
            print('Lyric: link start not found')
            return

        link_end = result.find('&amp;', link_start + 1)

        url = result[link_start:link_end]

        print('Lyrics url:', url)

        song_html = requests.get(url).content

        soup = BeautifulSoup(song_html, 'lxml')

        lyrics = soup.select(
            'div[class^="lyric-original"]')[0].get_text(strip=True, separator='\n').split('\n')

        grouped_lyrics = []
        current_items = []
        for i in lyrics:
            if len("\n".join(current_items)) + len(i) > 700 or len(current_items) > 17:
                grouped_lyrics.append("\n".join(current_items))
                current_items.clear()
            current_items.append(i)
        if len(current_items) < 8:
            grouped_lyrics[-1] += "\n" + "\n".join(current_items)
        else:
            grouped_lyrics.append("\n".join(current_items))

        return grouped_lyrics
    except Exception as e:
        print("Lyrics error:", e)
