from functools import partial
from collections import namedtuple
from urllib.parse import urlparse, parse_qs
from base64 import b64decode

from sqlalchemy import Column as BaseColumn, Integer, String, JSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy_utils import ArrowType
from bs4 import BeautifulSoup
import arrow
import requests

from rank import db

Column = partial(BaseColumn, nullable=False)


class HTMLParsingError(Exception):
    pass


class Site(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Query(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    @staticmethod
    def rotate(delta):
        accumulated_offset = Counter.increment_offset(delta)
        offset = accumulated_offset % Query.query.count()
        query = Query.query.order_by('name').offset(offset).limit(delta)
        return [x.name for x in query]


class Page(db.Model):
    id = Column(Integer, primary_key=True)
    url = Column(String)
    q = Column('query', String)
    text = Column(String)
    date_created = Column(ArrowType(timezone=True), default=arrow.now)
    contributor = Column(String)
    positions = Column(MutableList.as_mutable(JSON), nullable=True)

    def __repr__(self):
        return "<Page('{}', {!r})>".format(self.date_created, self.q)

    def get_text(self):
        return b64decode(self.text).decode('utf-8')

    def parse(self):
        soup = BeautifulSoup(self.get_text(), 'html.parser')

        Site_ = namedtuple('Site', 'url ad')
        sites = []

        divs = soup.select('div.organic.typo.typo_text_m')

        if not divs:
            raise HTMLParsingError('divs not found in page. Is it capcha?')

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

        interest = {s.name for s in Site.query}

        def prepare(page):
            items = []
            guarantee = False
            touched_organic = False
            n = 0
            for p in page.positions:
                if not p['ad']:
                    touched_organic = True
                    continue
                n += 1
                guarantee = guarantee or touched_organic
                site = domain(p['url'])
                if site not in interest:
                    continue
                items.append(dict(
                    site=site,
                    query=page.q,
                    update=page.date_created.timestamp,
                    position=n,
                    guarantee=guarantee,
                ))
            return items

        results = []

        for phrase in Query.query:
            page = (
                Page.query
                    .filter(Page.positions.isnot(None))
                    .filter(Page.q == phrase.name)
                    .order_by(Page.date_created.desc())
                    .first()
            )
            if page is not None:
                results.extend(prepare(page))

        return results


class Counter(db.Model):
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(Integer, default=0)
    date_changed = Column(ArrowType(timezone=True), default=arrow.now, onupdate=arrow.now)

    @classmethod
    def increment_offset(cls, delta):
        x = cls.query.filter_by(key='offset').first()
        if x is None:
            x = cls(key='offset', value=delta)
            db.session.add(x)
            current = 0
        else:
            current = x.value
            x.value = cls.value + delta
        db.session.commit()
        return current


def url_from_query(query):
    params = dict(text=query)
    return requests.Request(
        'GET', 'http://yandex.ru/search/', params=params).prepare().url


def query_from_url(url):
    query = parse_qs(urlparse(url).query)
    return query.get('text', [])[0]
