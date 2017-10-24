from functools import partial
from urllib.parse import urlparse, parse_qs
from base64 import b64decode
import random
import itertools

from sqlalchemy import Column as BaseColumn, Integer, String, JSON, Boolean
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.sql.expression import func
from sqlalchemy_utils import ArrowType
from bs4 import BeautifulSoup
import arrow
import requests

from rank import db, app
from rank.utils import domain

Column = partial(BaseColumn, nullable=False)


class HTMLParsingError(Exception):
    pass


class YandexCaptcha(Exception):
    pass


class Site(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class Phrase(db.Model):
    __tablename__ = 'query'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    last_parsed_date = Column(ArrowType(timezone=True))

    @classmethod
    def rotate(cls, n):
        q = cls.query
        q_1 = q.filter(cls.last_parsed_date.is_(None)).order_by(func.random()).limit(n)
        q_2 = q.filter(cls.last_parsed_date.isnot(None)).order_by(cls.last_parsed_date)
        names_random = [x.name for x in q_1]
        m = max(0, n - len(names_random))
        names = [x.name for x in q_2.limit(m * 5)]
        random.shuffle(names)
        return names_random + names[:m]


class Page(db.Model):
    id = Column(Integer, primary_key=True)
    url = Column(String)
    q = Column('query', String)
    text = Column(String)
    date_created = Column(ArrowType(timezone=True), default=arrow.now)
    contributor = Column(String)
    positions = Column(MutableList.as_mutable(JSON), nullable=True)
    captcha = Column(Boolean, default=False)

    def __repr__(self):
        if self.date_created is None:
            d = None
        else:
            d = self.date_created.format('DD MMM HH:mm')
        return "<Page({!r}, {}, {!r}, {!r})>".format(self.contributor, self.id, d, self.q)

    def update_phrase(self):
        phrase = Phrase.query.filter_by(name=self.q).first()
        if phrase is None:
            app.logger.error('Phrase {!r} should exist but not found'.format(self.q))
            return
        phrase.last_parsed_date = arrow.now()

    def get_text(self):
        return b64decode(self.text).decode('utf-8')

    def parse(self):
        yandex = 'yandex.ru' in self.url
        if yandex:
            return self._parse_yandex()
        return self._parse_google()

    def _parse_google(self):
        return []

    def _parse_yandex(self):

        soup = BeautifulSoup(self.get_text(), 'html.parser')

        captcha = bool(soup(href='captcha.min.css')) or bool(soup(href='captcha_random.min.css'))
        if captcha:
            raise YandexCaptcha()

        if bool(soup.select('div.misspell__message')):
            # Absolutely nothing was found by Yandex.
            return []

        divs = soup.select('div.organic.typo.typo_text_m')

        if not divs:
            raise HTMLParsingError('divs ".organic.typo.typo_text_m" not found in page')

        sites = []

        for n, div in enumerate(divs):
            aa = div.select('div.path.organic__path a')
            if not aa:
                app.logger.warning(
                    'div.path.organic__path a not found in {}-th parent div'.format(n))
                continue
            a = aa[0]
            url = a.text.replace('\n', '').replace(' ', '')
            ad = bool(div.select('div.label_color_yellow'))
            sites.append(dict(url=url, ad=ad))

        return sites

    @classmethod
    def pages_query(cls):
        phrases_subquery = db.session.query(Phrase.name)
        return (
            cls.query
            .distinct(Page.q)
            .filter(Page.positions.isnot(None))
            .filter(Page.q.in_(phrases_subquery))
            .order_by(cls.q, cls.date_created.desc())
        )

    @staticmethod
    def construct_results():
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

        return list(itertools.chain.from_iterable(
            prepare(x) for x in Page.pages_query()))


class Contributor(db.Model):
    id = Column(Integer, primary_key=True)
    date_created = Column(ArrowType(timezone=True), default=arrow.now)
    name = Column(String, default='')
    ip = Column(String)

    @classmethod
    def how_many(cls):
        moment = arrow.now().replace(hours=-1)
        return cls.query.distinct(cls.ip).filter(
            cls.date_created > moment).count()

    @classmethod
    def delay(cls, n):
        phrases = Phrase.query.count()
        workers = cls.how_many()
        cycle = app.config['CYCLE']

        try:
            d = cycle * workers * n / phrases
        except ZeroDivisionError:
            d = 0

        return int(max(d, app.config['MIN_DELAY']))


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
    return query.get('text', [''])[0]
