Requests-XML: XML Parsing for Humans
====================================

.. image:: https://travis-ci.org/erinxocon/requests-xml.svg?branch=master
    :target: https://travis-ci.org/erinxocon/requests-xml
.. image:: https://img.shields.io/pypi/v/requests-xml.svg?maxAge=2592000
    :target: https://pypi.python.org/pypi/requests-xml/
.. image:: https://img.shields.io/pypi/l/requests-xml.svg?maxAge=2592000
    :target: https://opensource.org/licenses/MIT

This library intends to make parsing XML as
simple and intuitive as possible.  It is related
to the amazing `requests-html <http://html.python-requests.org/>`_
and has much of the same experience, just with
some more support for pure XML!

When using this library you automatically get:

- *XPath Selectors*, for the *brave* at heart.
- *Simple Search/Find* for the *faint* at heart.
- XML to JSON conversion thanks to `xmljson <https://github.com/sanand0/xmljson/>`_
- Mocked user-agent (like a real web browser).
- Connection–pooling and cookie persistence.
- The Requests experience you know and love, with magical XML parsing abilities.


Installation
============

.. code-block:: shell

    $ pipenv install requests-xml
    ✨🍰✨

Only **Python 3.6** is supported.


Tutorial & Usage
================

Make a GET request to `nasa.gov <https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss/>`_, using `Requests <https://docs.python-requests.org/>`_:

.. code-block:: pycon

    >>> from requests_xml import XMLSession
    >>> session = XMLSession()

    >>> r = session.get('https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss')

Grab a list of all links on the page, as–is (this only works for RSS feeds, or other feeds that happen to have `link` elements):

.. code-block:: pycon

    >>> r.xml.links
    ['http://www.nasa.gov/image-feature/from-the-earth-moon-and-beyond', 'http://www.nasa.gov/image-feature/jpl/pia21974/jupiter-s-colorful-cloud-belts', 'http://www.nasa.gov/', 'http://www.nasa.gov/image-feature/portrait-of-the-expedition-54-crew-on-the-space-station', ...]


XPath is the main supported way to query an element. (`learn more <https://msdn.microsoft.com/en-us/library/ms256086(v=vs.110).aspx>`_):

.. code-block:: pycon

   >>> item = r.html.xpath('//item', first=True)
   <Element 'item' >

Grab an text contents:

.. code-block:: pycon

    >>> print(item.text)
    The Beauty of Light
    http://www.nasa.gov/image-feature/the-beauty-of-light
    The Soyuz MS-08 rocket is launched with Soyuz Commander Oleg Artemyev of Roscosmos and astronauts Ricky Arnold and Drew Feustel of NASA, March 21, 2018, to join the crew of the Space Station.
    http://www.nasa.gov/image-feature/the-beauty-of-light
    Wed, 21 Mar 2018 14:12 EDT
    NASA Image of the Day

Introspect an elements attributes (`learn more <https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes>`_):

.. code-block:: pycon

    >>> rss = r.xml.xpath('//rss', first=True)
    >>> rss.attrs
    {'version': '2.0', '{http://www.w3.org/XML/1998/namespace}base': 'http://www.nasa.gov/'}

Render out an elements XML (note: namespaces will be applied to sub elements when grabbed):

.. code-block:: pycon

    >>> item.xml
    '<item xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:media="http://search.yahoo.com/mrss/"> <title>The Beauty of Light</title>\n <link>http://www.nasa.gov/image-feature/the-beauty-of-light</link>\n <description>The Soyuz MS-08 rocket is launched with Soyuz Commander Oleg Artemyev of Roscosmos and astronauts Ricky Arnold and Drew Feustel of NASA, March 21, 2018, to join the crew of the Space Station.</description>\n <enclosure url="http://www.nasa.gov/sites/default/files/thumbnails/image/nhq201803210005.jpg" length="1267028" type="image/jpeg"/>\n <guid isPermaLink="false">http://www.nasa.gov/image-feature/the-beauty-of-light</guid>\n <pubDate>Wed, 21 Mar 2018 14:12 EDT</pubDate>\n <source url="http://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss">NASA Image of the Day</source>\n</item>'


Select an element list within an element:

.. code-block:: pycon

    >>> item.xpath('//enclosure')[0].attrs['url']
    'http://www.nasa.gov/sites/default/files/thumbnails/image/nhq201803210005.jpg'

Search for links within an element:

.. code-block:: pycon

    >>> item.links
    ['http://www.nasa.gov/image-feature/the-beauty-of-light']


Search for text on the page.  This is useful if you wish to search out things between specific tags without using xpath:

.. code-block:: pycon

    >>> r.xml.search('<title>{}</title>)
    <Result ('NASA Image of the Day',) {}>


Using PyQuery we can use tag selectors to easily grab an element, with a simple syntax for ensuring the element
contains certain text.  This can be used as another easy way to grab an element without an xpath:

.. code-block:: pycon

    >>> light_title = r.xml.find('title', containing='The Beauty of Light')
    [<Element 'title' >]

    >>> light_title[0].text
    'The Beauty of Light'

Note: Xpath is preferred as it can allow you to get very specific with your element selection.  Find is intended to be
an easy way of grabbing all elements of a certain name.  Find does however accept CSS selectors, and if you can get those
to work with straight xml, go for it!

JSON Support
============

Using the great `xmljson <https://github.com/sanand0/xmljson/>`_ package, we convert the whole
XML document into a JSON representation.  There are six different conversion convetions available.
See the `about <https://github.com/sanand0/xmljson#about>`_ for what they are.  The default is `badgerfish`.
If you wish to use a different conversion convention, pass in a string with the name of the convetion to the
`.json()` method.


Using without Requests
======================

You can also use this library without Requests:

.. code-block:: pycon

    >>> from requests_xml import XML
    >>> doc = """
    <employees>
        <person>
            <name value="Alice"/>
        </person>
        <person>
            <name value="Bob"/>
        </person>
    </employees>
    """

    >>> xml = XML(xml=doc)
    >>> xml.json()
    {
        "employees": [{
            "person": {
                "name": {
                    "@value": "Alice"
                }
            }
        }, {
            "person": {
                "name": {
                    "@value": "Bob"
                }
            }
        }]
    }
