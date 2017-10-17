from functools import partial
from collections import namedtuple
from urllib.parse import urlparse, parse_qs
import base64

from sqlalchemy import Column as BaseColumn, Integer, String, JSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy_utils import ArrowType
from bs4 import BeautifulSoup
import arrow
import requests

from rank import db

Column = partial(BaseColumn, nullable=False)


class Site(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Query(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Page(db.Model):
    id = Column(Integer, primary_key=True)
    url = Column(String)
    q = Column('query', String)
    text = Column(String)
    date_created = Column(ArrowType(timezone=True), default=arrow.now)
    contributor = Column(String)
    positions = Column(MutableList.as_mutable(JSON), nullable=True)

    def __repr__(self):
        return "<Page({!r}, '{}')>".format(self.q, self.date_created)

    def get_text(self):
        return base64.b64decode(self.text).decode('utf-8')

    def parse(self):
        soup = BeautifulSoup(self.get_text(), 'html.parser')

        Site_ = namedtuple('Site', 'url ad')
        sites = []

        divs = soup.select('div.organic.typo.typo_text_m')

        for div in divs:
            a = div.select('div.path.organic__path a')[0]
            url = a.text.replace('\n', '').replace(' ', '')
            ad = bool(div.select('div.label_color_yellow'))
            sites.append(Site_(url, ad))

        return sites

    @staticmethod
    def construct_results():
        def domain(url):
            if not urlparse(url).scheme:
                url = 'http://' + url
            return urlparse(url).netloc

        def extract(pos, page, n, m):
            return dict(
                site=domain(pos['url']),
                query=page.q,
                update=page.date_created.timestamp,
                position=n,
                advertising=pos['ad'],
                advertising_position=m,
            )

        results = []

        query = Page.query.filter(
            Page.positions.isnot(None)).order_by(Page.date_created.desc())

        for page in query:
            ad_pos = {x['url']: n for n, x in enumerate(page.positions, start=1) if x['ad']}
            results.extend(
                extract(p, page, n, ad_pos.get(p['url']))
                for n, p in enumerate(page.positions, start=1)
            )

        interest = {s.name for s in Site.query}
        return [x for x in results if x['site'] in interest]


def url_from_query(query):
    params = dict(text=query)
    return requests.Request(
        'GET', 'http://yandex.ru/search/', params=params).prepare().url


def query_from_url(url):
    query = parse_qs(urlparse(url).query)
    return query.get('text', [])[0]


def new_phrases():
    return [q.name for q in Query.query]
