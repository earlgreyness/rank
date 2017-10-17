from flask import request
from flask_restful import Api, Resource

from rank import app, db
from rank.models import (
    url_from_query, Page, query_from_url,
    Query, Site)


class Donors(Resource):
    def get(self):
        phrases = Query.rotate(5)
        return {
            'delay': 4 * 60 * 1000,  # msec
            'donors': [url_from_query(x) for x in phrases],
        }


class Accept(Resource):
    def post(self):
        incoming = request.get_json(force=True)

        page = Page(
            url=incoming['url'],
            q=query_from_url(incoming['url']),
            text=incoming['text'],
            contributor=request.remote_addr,
        )
        db.session.add(page)
        db.session.commit()
        app.logger.info('Accepted {}'.format(page))

        return {'success': True}


def new(array, cls):
    db.session.query(cls).delete()
    for s in array:
        db.session.add(cls(name=s))
    db.session.commit()


class Queries(Resource):
    def post(self):
        queries = request.json['queries']
        app.logger.info('new queries: {}'.format(queries))
        new(queries, Query)
        return {'success': True}


class Sites(Resource):
    def post(self):
        sites = request.json['sites']
        app.logger.info('new sites: {}'.format(sites))
        new(sites, Site)
        return {'success': True}


class Result(Resource):
    def get(self):
        return Page.construct_results()


api = Api(app)
api.add_resource(Donors, '/api/donors')
api.add_resource(Accept, '/api/accept')
api.add_resource(Result, '/api/result')
api.add_resource(Queries, '/api/queries')
api.add_resource(Sites, '/api/sites')
