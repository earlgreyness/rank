from flask_restful import Api, Resource

from rank import app


class Donors(Resource):
    def get(self):
        donors = []
        return {
            'delay': 60 * 60,
            'donors': donors,
        }


class Accept(Resource):
    def post(self):
        return {'success': True}


api = Api(app)
api.add_resource(Donors, '/api/donors')
api.add_resource(Accept, '/api/accept')
