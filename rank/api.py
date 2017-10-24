from flask import request
from flask_restful import Api, Resource, abort

from rank import app, db
from rank.models import (
    url_from_query, Page, query_from_url,
    Phrase, Site, Contributor)


class Donors(Resource):
    def get(self):
        n = app.config['AMOUNT']
        phrases = Phrase.rotate(n)
        delay = Contributor.delay(n)
        db.session.add(Contributor(ip=request.remote_addr))
        db.session.commit()
        return {
            'delay': int(delay * 1000),  # msec
            'donors': [url_from_query(x) for x in phrases],
        }


class Accept(Resource):
    def post(self):
        incoming = request.get_json(force=True)
        try:
            url = incoming['url'].strip()
            text = incoming['text'].strip()
        except KeyError as e:
            app.logger.error('Key missing in json: {}. We got: {}'.format(e, incoming))
            abort(400)
        ip = request.remote_addr
        if not text:
            app.logger.error('From {} got empty text'.format(ip))
            abort(400)
        page = Page(url=url, q=query_from_url(url), text=text, contributor=ip)
        db.session.add(page)
        db.session.commit()
        app.logger.info('From {} accepted {!r}'.format(ip, page))

        return {'success': True}


def new(array, cls):
    db.session.query(cls).delete()
    collection = {x.strip() for x in array if x.strip()}
    for s in collection:
        db.session.add(cls(name=s))
    db.session.commit()


class Queries(Resource):
    def post(self):
        queries = request.json['queries']
        app.logger.info('new queries: {}'.format(queries))
        new(queries, Phrase)
        return {'success': True}

    def get(self):
        return {'queries': [x.name for x in Phrase.query.order_by('name')]}


class Sites(Resource):
    def post(self):
        sites = request.json['sites']
        app.logger.info('new sites: {}'.format(sites))
        new(sites, Site)
        return {'success': True}

    def get(self):
        return {'sites': [x.name for x in Site.query.order_by('name')]}


class Result(Resource):
    def get(self):
        return Page.construct_results()


api = Api(app)
api.add_resource(Donors, '/api/donors')
api.add_resource(Accept, '/api/accept')
api.add_resource(Result, '/api/result')
api.add_resource(Queries, '/api/queries')
api.add_resource(Sites, '/api/sites')
