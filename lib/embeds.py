from discord import Embed

from models.Song import Song

from lib.utils import convert_seconds_to_timestamp


def generate_add_to_queue_embed(song: Song, position: int) -> Embed:
    embed = Embed(
        title="Added to queue", description=f'**[{song.title}]({song.url})**\n`[{convert_seconds_to_timestamp(song.time)}]`')
    embed.set_image(url=song.image_url)
    embed.set_footer(text=f'#{position} in queue')
    return embed
