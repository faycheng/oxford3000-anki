import threading
import genanki
import requests

from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool


def parse(word, soup):
    mdict = {
        "senses": []
    }
    for sense in soup.find_all("span", {"class": "Sense"}):
        word_sense = {
            "def": None,
            "examples": []
        }
        if len(sense.find_all("span", {"class", "DEF"})) == 0:
            continue
        word_sense['def'] = str(
            str(sense.find_all("span", {"class", "DEF"})[0]).replace(
                "href=\"/dictionary",
                "href=\"https://www.ldoceonline.com/dictionary"
            )
        )
        for example in sense.find_all("span", {"class": "EXAMPLE"}):
            item = {
                "sound": "",
                "sentence": None,
            }
            if example.find_all("span", {"class": "speaker exafile fas fa-volume-up hideOnAmp"}):
                item['sound'] = example.find_all("span", {"class": "speaker exafile fas fa-volume-up hideOnAmp"})[0].attrs['data-src-mp3']
            item['sentence'] = str(example).replace(
                word,
                "<a href=\"{}\"><strong>{}</strong></a>".format(
                    "https://www.ldoceonline.com/dictionary/" + word,
                    word)
                )
            word_sense['examples'].append(item)
        mdict['senses'].append(word_sense)
    return mdict


def query(word):
    response = requests.get(
        "https://www.ldoceonline.com/dictionary/{}".format(word),
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        },
    )
    if response.status_code != 200:
        raise Exception("{} not found".format(word))
    html = response.content
    soup = BeautifulSoup(html, 'html.parser')
    return parse(word, soup)


word_model = genanki.Model(
    1024 * 1024,
    'Simple Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
    ],
    templates=[
        {
            'name': 'Word Card',
            'qfmt': '<div>{{Question}}</div>',
            'afmt': '<div>{{FrontSide}}<hr id="answer">{{Answer}}</div>',
        },
    ])

with open("./oxford-3000.txt") as fd:
    words = [line.strip() for line in fd.readlines()]

deck = genanki.Deck(
    2048 * 2048,
    "Oxford 3000"
)


def do(word):
    try:
        senses = query(word)['senses']
    except Exception as e:
        print(word, e)
        return
    for sense in senses:
        if len(sense['examples']) == 0:
            continue
        for example in sense['examples']:
            note = genanki.Note(
                model=word_model,
                fields=[example['sentence'], sense['def']]
            )
            print(example, sense['def'])
            return note


pool = ThreadPool(128)
notes = pool.map(do, words)
for note in notes:
    if note is not None:
        deck.add_note(note)
genanki.Package(deck).write_to_file("oxford-3000.apkg")
