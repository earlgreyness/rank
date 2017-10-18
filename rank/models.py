from functools import partial
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


class Phrase(db.Model):
    __tablename__ = 'query'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    @classmethod
    def rotate(cls, delta):
        accumulated_offset = Counter.increment_offset(delta)
        offset = accumulated_offset % cls.query.count()
        query = cls.query.order_by('name').offset(offset).limit(delta)
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
        return "<Page({}, '{}', {!r})>".format(self.id, self.date_created, self.q)

    def get_text(self):
        return b64decode(self.text).decode('utf-8')

    def parse(self):
        soup = BeautifulSoup(self.get_text(), 'html.parser')
        divs = soup.select('div.organic.typo.typo_text_m')

        if not divs:
            raise HTMLParsingError('divs not found in page. Is it capcha?')

        sites = []

        for div in divs:
            a = div.select('div.path.organic__path a')[0]
            url = a.text.replace('\n', '').replace(' ', '')
            ad = bool(div.select('div.label_color_yellow'))
            sites.append(dict(url=url, ad=ad))

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
        phrases = {x.name.strip() for x in Phrase.query if x.name.strip()}
        n = len(phrases)
        pages_qry = (
            Page.query
            .filter(Page.positions.isnot(None))
            .filter(Page.q.in_(phrases))
            .filter(Page.date_created > arrow.now().replace(hours=-6))
            .order_by(Page.date_created.desc())
            .limit(n * 2)
        )
        seen = set()
        for page in pages_qry:
            if page.q in seen:
                continue
            results.extend(prepare(page))
            seen.add(page.q)

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
