from rank.models import Page, query_from_url
from rank.utils import handle_exceptions
from rank import db, app


@handle_exceptions
def main():
    pages = Page.query.filter(Page.positions.is_(None))

    for page in pages:
        app.logger.info('Working on {!r}'.format(page))
        page.positions = [{'url': x.url, 'ad': x.ad} for x in page.parse()]
        page.q = query_from_url(page.url)

    db.session.commit()


if __name__ == '__main__':
    main()
