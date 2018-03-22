import sys
import asyncio
import json
from io import BytesIO
from urllib.parse import urlparse, urlunparse, urljoin
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import TimeoutError
from functools import partial
from typing import Set, Union, List, MutableMapping, Optional, Mapping

import requests
from pyquery import PyQuery
from fake_useragent import UserAgent
import lxml
from lxml import etree
from parse import search as parse_search
from parse import findall, Result
from w3lib.encoding import html_to_unicode

DEFAULT_ENCODING = 'utf-8'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8'

useragent = None

# Typing.
_XPath = Union[List[str], List['Element'], str, 'Element']
_Result = List['Result']
_XML = Union[str, bytes]
_BaseXML = str
_UserAgent = str
_DefaultEncoding = str
_RawXML = bytes
_Encoding = str
_LXML = etree.Element
_Text = str
_Search = Result
_Containing = Union[str, List[str]]
_Links = Set[str]
_Attrs = MutableMapping
_Find = Union[List['Element'], 'Element']

# Sanity checking.
try:
    assert sys.version_info.major == 3
    assert sys.version_info.minor > 5
except AssertionError:
    raise RuntimeError('Requests-XML requires Python 3.6+!')


class BaseParser:
    """A basic XML/Element Parser, for Humans.

    :param element: The element from which to base the parsing upon.
    :param default_encoding: Which encoding to default to.
    :param xml: XML from which to base the parsing upon (optional).

    """

    def __init__(self, *, element, session: 'XMLSession' = None, default_encoding: _DefaultEncoding = DEFAULT_ENCODING, xml: _XML = None) -> None:
        self.element = element
        self.session = session or XMLSession()
        self.default_encoding = default_encoding
        self._encoding = None
        self._xml = xml.encode(DEFAULT_ENCODING) if isinstance(xml, str) else xml
        self._lxml = None
        self._pq = None
        self._docinfo = None
        self._json = None


    @property
    def raw_xml(self) -> _RawXML:
        """Bytes representation of the XML content.
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        if self._xml:
            return self._xml
        else:
            return etree.tostring(self.element, encoding='unicode').strip().encode(self.encoding)


    @property
    def xml(self) -> _BaseXML:
        """Unicode representation of the XML content
        (`learn more <http://www.diveintopython3.net/strings.html>`_).
        """
        if self._xml:
            return self.raw_xml.decode(self.encoding)
        else:
            return etree.tostring(self.element, encoding='unicode').strip()


    @xml.setter
    def xml(self, xml: str) -> None:
        self._xml = xml.encode(self.encoding)


    @raw_xml.setter
    def raw_xml(self, xml: bytes) -> None:
        """Property setter for self.html."""
        self._xml = xml


    @property
    def pq(self) -> PyQuery:
        """`PyQuery <https://pythonhosted.org/pyquery/>`_ representation
        of the :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        if self._pq is None:
            self._pq = PyQuery(self.raw_xml)

        return self._pq

    @property
    def lxml(self) -> _LXML:
        """`lxml <http://lxml.de>`_ representation of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        if self._lxml is None:
            self._lxml = etree.fromstring(self.raw_xml)

        return self._lxml

    @property
    def text(self) -> _Text:
        """The text content of the
        :class:`Element <Element>` or :class:`HTML <HTML>`.
        """
        return self.pq.text()


    @property
    def links(self) -> _Links:
        """All found links on page, in as–is form.  Only works for Atom feeds."""
        return list(set(x.text for x in self.xpath('//link')))


    @property
    def docinfo(self) -> etree.DocInfo:
        if self._docinfo is None:
            self._docinfo = etree.parse(BytesIO(self.raw_xml)).docinfo

        return self._docinfo


    @property
    def xml_version(self) -> _Text:
        return self.docinfo.xml_version


    @property
    def root_tag(self) -> _Text:
        return self.docinfo.root_name


    @property
    def encoding(self) -> _Encoding:
        """The encoding string to be used, extracted from the XML and
        :class:`XMLResponse <XMLResponse>` header.
        """
        if self._encoding:
            return self._encoding

        # Scan meta tags for charset.
        if self._xml:
            self._encoding = html_to_unicode(self.default_encoding, self._xml)[0]

        return self._encoding if self._encoding else self.default_encoding


    @encoding.setter
    def encoding(self, enc: str) -> None:
        """Property setter for self.encoding."""
        self._encoding = enc


    def json(self, conversion: _Text = 'badgerfish') -> Mapping:
        """A JSON Representation of the XML.  Default is badgerfish.
        :param conversion: Which conversion method to use. (`learn more <https://github.com/sanand0/xmljson#conventions>`_)
        """
        if not self._json:

            if conversion is 'badgerfish':
                from xmljson import badgerfish as serializer

            elif conversion is 'abdera':
                from xmljson import abdera as serializer

            elif conversion is 'cobra':
                from xmljson import cobra as serializer

            elif conversion is 'gdata':
                from xmljson import gdata as serializer

            elif conversion is 'parker':
                from xmljson import parker as serializer

            elif conversion is 'yahoo':
                from xmljson import yahoo as serializer

            self._json = json.dumps(serializer.data(etree.fromstring(self.xml)))

        return self._json


    def xpath(self, selector: str, *, first: bool = False, _encoding: str = None) -> _XPath:
        """Given an XPath selector, returns a list of
        :class:`Element <Element>` objects or a single one.

        :param selector: XPath Selector to use.
        :param clean: Whether or not to sanitize the found HTML of ``<script>`` and ``<style>`` tags.
        :param first: Whether or not to return just the first result.
        :param _encoding: The encoding format.

        If a sub-selector is specified (e.g. ``//a/@href``), a simple
        list of results is returned.

        See W3School's `XPath Examples
        <https://www.w3schools.com/xml/xpath_examples.asp>`_
        for more details.

        If ``first`` is ``True``, only returns the first
        :class:`Element <Element>` found.
        """
        selected = self.lxml.xpath(selector)

        elements = [
            Element(element=selection, default_encoding=_encoding or self.encoding)
            if not isinstance(selection, etree._ElementUnicodeResult) else str(selection)
            for selection in selected
        ]

        return _get_first_or_list(elements, first)


    def search(self, template: str, first: bool = False) -> _Result:
        """Search the :class:`Element <Element>` for the given parse
        template.

        :param template: The Parse template to use.
        """
        elements = [r for r in findall(template, self.xml)]

        return _get_first_or_list(elements, first)


    def find(self, selector: str = '*', containing: _Containing = None, first: bool = False, _encoding: str = None) -> _Find:
            """Given a simple element name, returns a list of
            :class:`Element <Element>` objects or a single one.
            :param selector: Element name to find.
            :param containing: If specified, only return elements that contain the provided text.
            :param first: Whether or not to return just the first result.
            :param _encoding: The encoding format.
            If ``first`` is ``True``, only returns the first
            :class:`Element <Element>` found.
            """

            # Convert a single containing into a list.
            if isinstance(containing, str):
                containing = [containing]

            encoding = _encoding or self.encoding
            elements = [
                Element(element=found, default_encoding=encoding)
                for found in self.pq(selector)
            ]

            if containing:
                elements_copy = elements.copy()
                elements = []

                for element in elements_copy:
                    if any([c.lower() in element.text.lower() for c in containing]):
                        elements.append(element)

                elements.reverse()

            return _get_first_or_list(elements, first)


class Element(BaseParser):
    """An element of HTML.

    :param element: The element from which to base the parsing upon.
    :param default_encoding: Which encoding to default to.
    """

    __slots__ = [
        'element', 'default_encoding', '_encoding',
        '_xml', '_lxml', '_pq', '_attrs', 'session'
    ]

    def __init__(self, *, element, default_encoding: _DefaultEncoding = None) -> None:
        super(Element, self).__init__(element=element, default_encoding=default_encoding)
        self.element = element
        self._attrs = None

    def __repr__(self) -> str:
        attrs = ['{}={}'.format(attr, repr(self.attrs[attr])) for attr in self.attrs]
        return "<Element {} {}>".format(repr(self.element.tag), ' '.join(attrs))

    @property
    def attrs(self) -> _Attrs:
        """Returns a dictionary of the attributes of the :class:`Element <Element>`
        (`learn more <https://www.w3schools.com/tags/ref_attributes.asp>`_).
        """
        if self._attrs is None:
            self._attrs = {k: v for k, v in self.element.items()}

            # Split class and rel up, as there are ussually many of them:
            for attr in ['class', 'rel']:
                if attr in self._attrs:
                    self._attrs[attr] = tuple(self._attrs[attr].split())

        return self._attrs


class XML(BaseParser):
    """An XML document, ready for parsing.

    :param xml: XML from which to base the parsing upon (optional).
    :param default_encoding: Which encoding to default to.
    """

    def __init__(self, *, xml: _XML, default_encoding: str = DEFAULT_ENCODING) -> None:

        # Convert incoming unicode HTML into bytes.
        if isinstance(xml, str):
            xml = xml.encode(DEFAULT_ENCODING)

        super(XML, self).__init__(
            # Convert unicode HTML to bytes.
            element=PyQuery(xml)('xml') or PyQuery(f'<xml>{xml}</xml>')('xml'),
            xml=xml,
            default_encoding=default_encoding
        )

    def __repr__(self) -> str:
        return f"<XML element={self.element!r}>"


class XMLResponse(requests.Response):
    """An XML-enabled :class:`requests.Response <requests.Response>` object.
    Effectively the same, but with an intelligent ``.xml`` property added.
    The json method has also been changed to show a json representation of the xml.
    """

    def __init__(self) -> None:
        super(XMLResponse, self).__init__()
        self._xml = None # type: HTML

    @property
    def xml(self) -> XML:
        if not self._xml:
            self._xml = XML(xml=self.content, default_encoding=self.encoding)

        return self._xml


    @classmethod
    def _from_response(cls, response):
        xml_r = cls()
        xml_r.__dict__.update(response.__dict__)
        return xml_r


def user_agent(style=None) -> _UserAgent:
    """Returns an apparently legit user-agent, if not requested one of a specific
    style. Defaults to a Chrome-style User-Agent.
    """
    global useragent
    if (not useragent) and style:
        useragent = UserAgent()

    return useragent[style] if style else DEFAULT_USER_AGENT


def _get_first_or_list(l, first=False):
    if first:
        try:
            return l[0]
        except IndexError:
            return None
    else:
        return l


class XMLSession(requests.Session):
    """A consumable session, for cookie persistence and connection pooling,
    amongst other things.
    """

    def __init__(self, mock_browser=True):
        super(XMLSession, self).__init__()

        # Mock a web browser's user agent.
        if mock_browser:
            self.headers['User-Agent'] = user_agent()

        self.hooks = {'response': self._handle_response}

    @staticmethod
    def _handle_response(response, **kwargs) -> XMLResponse:
        """Requests HTTP Response handler. Attaches .html property to
        class:`requests.Response <requests.Response>` objects.
        """
        if not response.encoding:
            response.encoding = DEFAULT_ENCODING

        return response

    def request(self, *args, **kwargs) -> XMLResponse:
        """Makes an HTTP Request, with mocked User–Agent headers.
        Returns a class:`HTTPResponse <HTTPResponse>`.
        """
        # Convert Request object into HTTPRequest object.
        r = super(XMLSession, self).request(*args, **kwargs)

        return XMLResponse._from_response(r)


class AsyncXMLSession(requests.Session):
    """ An async consumable session. """

    def __init__(self, loop=None, workers=None,
                 mock_browser: bool = True, *args, **kwargs):
        """ Set or create an event loop and a thread pool.

            :param loop: Asyncio lopp to use.
            :param workers: Amount of threads to use for executing async calls.
                If not pass it will default to the number of processors on the
                machine, multiplied by 5. """
        super().__init__(*args, **kwargs)

        # Mock a web browser's user agent.
        if mock_browser:
            self.headers['User-Agent'] = user_agent()

        self.hooks["response"].append(self.response_hook)

        self.loop = loop or asyncio.get_event_loop()
        self.thread_pool = ThreadPoolExecutor(max_workers=workers)

    @staticmethod
    def response_hook(response, **kwargs) -> XMLResponse:
        """ Change response enconding and replace it by a HTMLResponse. """
        response.encoding = DEFAULT_ENCODING
        return XMLResponse._from_response(response)

    def request(self, *args, **kwargs):
        """ Partial original request func and run it in a thread. """
        func = partial(super().request, *args, **kwargs)
        return self.loop.run_in_executor(self.thread_pool, func)
