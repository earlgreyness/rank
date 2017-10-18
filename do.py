from rank.models import Page, query_from_url, HTMLParsingError, YandexCaptcha
from rank.utils import handle_exceptions
from rank import db, app


@handle_exceptions
def main():
    pages = Page.query.filter(
        Page.positions.is_(None), Page.captcha.is_(False)).order_by('id')

    for page in pages:
        page.q = query_from_url(page.url)
        try:
            page.positions = page.parse()
        except YandexCaptcha:
            page.captcha = True
            app.logger.warning('Capcha in {!r}'.format(page))
        except HTMLParsingError as e:
            app.logger.error('Error parsing {!r}: {}'.format(page, e))
        else:
            page.text = ''
            app.logger.info(
                'Parsed {} positions for {!r}'.format(len(page.positions), page))

    db.session.commit()


if __name__ == '__main__':
    main()
