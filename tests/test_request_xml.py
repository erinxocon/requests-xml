import os
from functools import partial

import pytest

from requests_xml import XMLSession, AsyncXMLSession, XML
from requests_file import FileAdapter

session = XMLSession()
session.mount('file:///', FileAdapter())


def get():
    path = os.path.sep.join((os.path.dirname(os.path.abspath(__file__)), 'nasa.rss'))
    url = 'file:///{}'.format(path)

    return session.get(url)


@pytest.fixture
def async_get(event_loop):
    """ AsyncSession cannot be created global since it will create
        a different loop from pytest-asyncio. """
    async_session = AsyncXMLSession()
    async_session.mount('file:///', FileAdapter())
    path = os.path.sep.join((os.path.dirname(os.path.abspath(__file__)), 'nasa.rss'))
    url = 'file:///{}'.format(path)

    return partial(async_session.get, url)


@pytest.mark.ok
def test_file_get():
    r = get()
    assert r.status_code == 200


@pytest.mark.ok
@pytest.mark.asyncio
async def test_async_file_get(async_get):
    r = await async_get()
    assert r.status_code == 200


@pytest.mark.ok
def test_attrs():
    r = get()
    rss = r.xml.xpath('/rss', first=True)

    assert 'version' in rss.attrs
    assert len(rss.attrs) == 2


@pytest.mark.ok
def test_links():
    r = get()

    assert len(r.xml.links) == 61


@pytest.mark.ok
@pytest.mark.asyncio
async def test_async_links(async_get):
    r = await async_get()

    assert len(r.xml.links) == 61


@pytest.mark.ok
def test_search():
    r = get()
    style = r.xml.search('NASA {} of the Day')[0][0]
    assert style == 'Image'


@pytest.mark.ok
def test_xpath():
    r = get()
    xml = r.xml.xpath('/rss', first=True)
    assert '2.0' in xml.attrs['version']

    items = r.xml.xpath('//item')
    assert len(items) == 60


@pytest.mark.ok
def test_XML_loading():
    doc = """
    <item>
      <title>Under the Midnight Sun</title>
      <link>http://www.nasa.gov/image-feature/under-the-midnight-sun</link>
      <description>In September 2017, a new iceberg calved from Pine Island Glacier—one of the main outlets where the West Antarctic Ice Sheet flows into the ocean.</description>
      <enclosure url="http://www.nasa.gov/sites/default/files/thumbnails/image/pineisland_oli_2017349_lrg.jpg" length="5783827" type="image/jpeg"/>
      <guid isPermaLink="false">http://www.nasa.gov/image-feature/under-the-midnight-sun</guid>
      <pubDate>Fri, 29 Dec 2017 10:23 EST</pubDate>
      <source url="http://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss">NASA Image of the Day</source>
    </item>
    """
    xml = XML(xml=doc)

    assert 'http://www.nasa.gov/image-feature/under-the-midnight-sun' in xml.links
    assert isinstance(xml.raw_xml, bytes)
    assert isinstance(xml.xml, str)



if __name__ == '__main__':
    test_containing()