# -*- coding: utf-8 -*-
"""Tests for the page module."""
#
# (C) Pywikibot team, 2008-2020
#
# Distributed under the terms of the MIT license.
#
import pickle
import re

from contextlib import suppress

import pywikibot
import pywikibot.page

from pywikibot import config, InvalidTitle
from pywikibot.tools import suppress_warnings

from tests.aspects import (
    DefaultDrySiteTestCase, DefaultSiteTestCase, SiteAttributeTestCase,
    TestCase, unittest,
)
from tests import mock


EMPTY_TITLE_RE = r'Title must be specified and not empty if source is a Site\.'
INVALID_TITLE_RE = r'The link does not contain a page title'
NO_PAGE_RE = r"doesn't exist\."


class TestLinkObject(SiteAttributeTestCase):

    """Test cases for Link objects."""

    sites = {
        'enwiki': {
            'family': 'wikipedia',
            'code': 'en',
        },
        'frwiki': {
            'family': 'wikipedia',
            'code': 'fr',
        },
        'itwikt': {
            'family': 'wiktionary',
            'code': 'it',
        },
        'enws': {
            'family': 'wikisource',
            'code': 'en',
        },
        'itws': {
            'family': 'wikisource',
            'code': 'it',
        },
    }

    cached = True

    namespaces = {0: [''],        # en.wikipedia.org namespaces for testing
                  1: ['Talk:'],   # canonical form first, then others
                  2: ['User:'],   # must end with :
                  3: ['User talk:', 'User_talk:'],
                  4: ['Wikipedia:', 'Project:', 'WP:'],
                  5: ['Wikipedia talk:', 'Project talk:', 'Wikipedia_talk:',
                      'Project_talk:', 'WT:'],
                  6: ['File:'],
                  7: ['Image talk:', 'Image_talk:'],
                  8: ['MediaWiki:'],
                  9: ['MediaWiki talk:', 'MediaWiki_talk:'],
                  10: ['Template:'],
                  11: ['Template talk:', 'Template_talk:'],
                  12: ['Help:'],
                  13: ['Help talk:', 'Help_talk:'],
                  14: ['Category:'],
                  15: ['Category talk:', 'Category_talk:'],
                  100: ['Portal:'],
                  101: ['Portal talk:', 'Portal_talk:'],
                  }
    titles = {
        # just a bunch of randomly selected titles
        # input format                  : expected output format
        'Cities in Burkina Faso':        'Cities in Burkina Faso',
        'eastern Sayan':                 'Eastern Sayan',
        'The_Addams_Family_(pinball)':   'The Addams Family (pinball)',
        'Hispanic  (U.S.  Census)':      'Hispanic (U.S. Census)',
        'Stołpce':                       'Stołpce',
        'Nowy_Sącz':                     'Nowy Sącz',
        'battle of Węgierska  Górka':    'Battle of Węgierska Górka',
    }
    # random bunch of possible section titles
    sections = ['',
                '#Phase_2',
                '#History',
                '#later life',
                ]

    def testNamespaces(self):
        """Test that Link() normalizes namespace names."""
        for num in self.namespaces:
            for prefix in self.namespaces[num]:
                link = pywikibot.page.Link(
                    prefix + list(self.titles.keys())[0], self.enwiki)
                self.assertEqual(link.namespace, num)
                # namespace prefixes are case-insensitive
                lowered_link = pywikibot.page.Link(
                    prefix.lower() + list(self.titles.keys())[1], self.enwiki)
                self.assertEqual(lowered_link.namespace, num)

    def testTitles(self):
        """Test that Link() normalizes titles."""
        for title in self.titles:
            for num in (0, 1):
                link = pywikibot.page.Link(self.namespaces[num][0] + title,
                                           self.enwiki)
                self.assertEqual(link.title, self.titles[title])
                # prefixing name with ":" shouldn't change result
                prefixed_link = pywikibot.page.Link(
                    ':' + self.namespaces[num][0] + title, self.enwiki)
                self.assertEqual(prefixed_link.title, self.titles[title])

    def testHashCmp(self):
        """Test hash comparison."""
        # All links point to en:wikipedia:Test
        l1 = pywikibot.page.Link('Test', source=self.enwiki)
        l2 = pywikibot.page.Link('en:Test', source=self.frwiki)
        l3 = pywikibot.page.Link('wikipedia:en:Test', source=self.itwikt)

        def assertHashCmp(link1, link2):
            self.assertEqual(link1, link2)
            self.assertEqual(hash(link1), hash(link2))

        assertHashCmp(l1, l2)
        assertHashCmp(l1, l3)
        assertHashCmp(l2, l3)

        # fr:wikipedia:Test
        other = pywikibot.page.Link('Test', source=self.frwiki)

        self.assertNotEqual(l1, other)
        self.assertNotEqual(hash(l1), hash(other))

    def test_ns_title(self):
        """Test that title is returned with correct namespace."""
        l1 = pywikibot.page.Link('Indice:Test', source=self.itws)
        self.assertEqual(l1.ns_title(), 'Index:Test')
        self.assertEqual(l1.ns_title(onsite=self.enws), 'Index:Test')

        # wikisource:it kept Autore as canonical name
        l2 = pywikibot.page.Link('Autore:Albert Einstein', source=self.itws)
        self.assertEqual(l2.ns_title(), 'Autore:Albert Einstein')
        self.assertEqual(l2.ns_title(onsite=self.enws),
                         'Author:Albert Einstein')

        # Translation namespace does not exist on wikisource:it
        l3 = pywikibot.page.Link('Translation:Albert Einstein',
                                 source=self.enws)
        self.assertEqual(l3.ns_title(), 'Translation:Albert Einstein')
        self.assertRaisesRegex(pywikibot.Error,
                               'No corresponding namespace found for '
                               'namespace Translation: on wikisource:it.',
                               l3.ns_title,
                               onsite=self.itws)


class TestPageObjectEnglish(TestCase):

    """Test Page Object using English Wikipedia."""

    family = 'wikipedia'
    code = 'en'

    cached = True

    def testGeneral(self):
        """Test general features of a page."""
        site = self.get_site()
        mainpage = self.get_mainpage()
        maintalk = mainpage.toggleTalkPage()

        family_name = (site.family.name + ':'
                       if pywikibot.config2.family != site.family.name
                       else '')
        self.assertEqual(str(mainpage), '[[{}{}:{}]]'
                                        .format(family_name, site.code,
                                                mainpage.title()))
        self.assertLess(mainpage, maintalk)

    def testHelpTitle(self):
        """Test title() method options in Help namespace."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'Help:Test page#Testing')
        ns_name = 'Help'
        if site.namespaces[12][0] != ns_name:
            ns_name = site.namespaces[12][0]
        self.assertEqual(p1.title(),
                         ns_name + ':Test page#Testing')
        self.assertEqual(p1.title(underscore=True),
                         ns_name + ':Test_page#Testing')
        self.assertEqual(p1.title(with_ns=False),
                         'Test page#Testing')
        self.assertEqual(p1.title(with_section=False),
                         ns_name + ':Test page')
        self.assertEqual(p1.title(with_ns=False, with_section=False),
                         'Test page')
        self.assertEqual(p1.title(as_url=True),
                         ns_name + '%3ATest_page%23Testing')
        self.assertEqual(p1.title(as_link=True, insite=site),
                         '[[' + ns_name + ':Test page#Testing]]')
        self.assertEqual(
            p1.title(as_link=True, force_interwiki=True, insite=site),
            '[[en:' + ns_name + ':Test page#Testing]]')
        self.assertEqual(p1.title(as_link=True, textlink=True, insite=site),
                         p1.title(as_link=True, textlink=False, insite=site))
        self.assertEqual(p1.title(as_link=True, with_ns=False, insite=site),
                         '[[' + ns_name + ':Test page#Testing|Test page]]')
        self.assertEqual(p1.title(as_link=True, force_interwiki=True,
                                  with_ns=False, insite=site),
                         '[[en:' + ns_name + ':Test page#Testing|Test page]]')
        self.assertEqual(p1.title(as_link=True, textlink=True,
                                  with_ns=False, insite=site),
                         p1.title(as_link=True, textlink=False,
                                  with_ns=False, insite=site))

    def testFileTitle(self):
        """Test title() method options in File namespace."""
        # also test a page with non-ASCII chars and a different namespace
        site = self.get_site()
        p2 = pywikibot.Page(site, 'File:Jean-Léon Gérôme 003.jpg')
        ns_name = 'File'
        if site.namespaces[6][0] != ns_name:
            ns_name = site.namespaces[6][0]
        self.assertEqual(p2.title(),
                         'File:Jean-Léon Gérôme 003.jpg')
        self.assertEqual(p2.title(underscore=True),
                         'File:Jean-Léon_Gérôme_003.jpg')
        self.assertEqual(p2.title(with_ns=False),
                         'Jean-Léon Gérôme 003.jpg')
        self.assertEqual(p2.title(with_section=False),
                         'File:Jean-Léon Gérôme 003.jpg')
        self.assertEqual(p2.title(with_ns=False, with_section=False),
                         'Jean-Léon Gérôme 003.jpg')
        self.assertEqual(p2.title(as_url=True),
                         'File%3AJean-L%C3%A9on_G%C3%A9r%C3%B4me_003.jpg')
        self.assertEqual(p2.title(as_link=True, insite=site),
                         '[[File:Jean-Léon Gérôme 003.jpg]]')
        self.assertEqual(
            p2.title(as_link=True, force_interwiki=True, insite=site),
            '[[en:File:Jean-Léon Gérôme 003.jpg]]')
        self.assertEqual(p2.title(as_link=True, textlink=True, insite=site),
                         '[[:File:Jean-Léon Gérôme 003.jpg]]')
        self.assertEqual(p2.title(as_filename=True),
                         'File_Jean-Léon_Gérôme_003.jpg')
        self.assertEqual(
            p2.title(as_link=True, with_ns=False, insite=site),
            '[[File:Jean-Léon Gérôme 003.jpg|Jean-Léon Gérôme 003.jpg]]')
        self.assertEqual(
            p2.title(as_link=True, force_interwiki=True,
                     with_ns=False, insite=site),
            '[[en:File:Jean-Léon Gérôme 003.jpg|Jean-Léon Gérôme 003.jpg]]')
        self.assertEqual(
            p2.title(as_link=True, textlink=True,
                     with_ns=False, insite=site),
            '[[:File:Jean-Léon Gérôme 003.jpg|Jean-Léon Gérôme 003.jpg]]')

    def testImageAndDataRepository(self):
        """Test image_repository and data_repository page attributes."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'Help:Test page#Testing')
        self.assertIsInstance(p1.image_repository, pywikibot.site.APISite)
        self.assertEqual(p1.image_repository,
                         pywikibot.site.APISite('commons', 'commons'))

        p2 = pywikibot.Page(site, 'File:Jean-Léon Gérôme 003.jpg')
        self.assertIsInstance(p2.data_repository, pywikibot.site.APISite)
        self.assertEqual(p2.data_repository,
                         pywikibot.site.APISite('wikidata', 'wikidata'))

    def test_creation(self):
        """Test Page.oldest_revision."""
        mainpage = self.get_mainpage()
        self.assertEqual(mainpage.oldest_revision.user, 'TwoOneTwo')
        self.assertIsInstance(mainpage.oldest_revision.timestamp,
                              pywikibot.Timestamp)


class TestPageObject(DefaultSiteTestCase):

    """Test Page object."""

    cached = True

    def testSite(self):
        """Test site() method."""
        mainpage = self.get_mainpage()
        self.assertEqual(mainpage.site, self.site)

    def testNamespace(self):
        """Test namespace() method."""
        mainpage = self.get_mainpage()
        maintalk = mainpage.toggleTalkPage()

        if ':' not in mainpage.title():
            self.assertEqual(mainpage.namespace(), 0)
        self.assertEqual(maintalk.namespace(), mainpage.namespace() + 1)

        badpage = self.get_missing_article()
        self.assertEqual(badpage.namespace(), 0)

    def testBasePageConstructor(self):
        """Test BasePage constructor."""
        site = self.get_site()

        # Should not raise an error as the constructor only requires
        # the site parameter.
        # Empty string or None as title raises error.
        page = pywikibot.page.BasePage(site)
        self.assertRaisesRegex(InvalidTitle, INVALID_TITLE_RE, page.title)
        page = pywikibot.page.BasePage(site, title='')
        self.assertRaisesRegex(InvalidTitle, INVALID_TITLE_RE, page.title)
        self.assertRaisesRegex(ValueError, 'Title cannot be None.',
                               pywikibot.page.BasePage, site, title=None)

    def testPageConstructor(self):
        """Test Page constructor."""
        site = self.get_site()
        mainpage = self.get_mainpage()

        # Test that Page() needs a title when Site is used as source.
        self.assertRaisesRegex(ValueError, EMPTY_TITLE_RE,
                               pywikibot.Page, site)
        self.assertRaisesRegex(ValueError, EMPTY_TITLE_RE,
                               pywikibot.Page, site, '')

        # Test Page as source.
        p1 = pywikibot.Page(mainpage)
        self.assertEqual(p1, mainpage)

        # Test not valid source.
        self.assertRaisesRegex(pywikibot.Error,
                               r"Invalid argument type '<\w* '\w*'>' in "
                               'Page initializer: dummy',
                               pywikibot.Page, 'dummy')

    def testTitle(self):
        """Test title() method options in article namespace."""
        # at last test article namespace
        site = self.get_site()
        p2 = pywikibot.Page(site, 'Test page')
        self.assertEqual(p2.title(),
                         'Test page')
        self.assertEqual(p2.title(underscore=True),
                         'Test_page')
        self.assertEqual(p2.title(),
                         p2.title(with_ns=False))
        self.assertEqual(p2.title(),
                         p2.title(with_section=False))
        self.assertEqual(p2.title(as_url=True),
                         p2.title(underscore=True))
        self.assertEqual(p2.title(as_link=True, insite=site),
                         '[[Test page]]')
        self.assertEqual(p2.title(as_filename=True),
                         p2.title(underscore=True))
        self.assertEqual(p2.title(underscore=True),
                         p2.title(underscore=True, with_ns=False))
        self.assertEqual(p2.title(underscore=True),
                         p2.title(underscore=True, with_section=False))
        self.assertEqual(p2.title(underscore=True, as_url=True),
                         p2.title(underscore=True))
        self.assertEqual(p2.title(underscore=True, as_link=True, insite=site),
                         p2.title(as_link=True, insite=site))
        self.assertEqual(p2.title(underscore=True, as_filename=True),
                         p2.title(underscore=True))
        self.assertEqual(p2.title(),
                         p2.title(with_ns=False, with_section=False))
        self.assertEqual(p2.title(as_url=True),
                         p2.title(with_ns=False, as_url=True))
        self.assertEqual(p2.title(as_link=True, insite=site),
                         p2.title(with_ns=False, as_link=True, insite=site))
        self.assertEqual(p2.title(as_filename=True),
                         p2.title(with_ns=False, as_filename=True))
        self.assertEqual(p2.title(with_ns=False, as_link=True,
                                  force_interwiki=True, insite=site),
                         '[[' + site.code + ':Test page|Test page]]')

        title1 = 'Test Page (bracketed)'
        title2 = 'Test Page (bracketed) (bracketed)'

        self.assertEqual(
            pywikibot.Page(site, title1).title(without_brackets=True),
            'Test Page'
        )
        self.assertEqual(
            pywikibot.Page(site, title2).title(without_brackets=True),
            'Test Page (bracketed)'
        )

    def testSection(self):
        """Test section() method."""
        # use same pages as in previous test
        site = self.get_site()
        p1 = pywikibot.Page(site, 'Help:Test page#Testing')
        p2 = pywikibot.Page(site, 'File:Jean-Léon Gérôme 003.jpg')
        self.assertEqual(p1.section(), 'Testing')
        self.assertIsNone(p2.section())

    def testIsTalkPage(self):
        """Test isTalkPage() method."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'First page')
        p2 = pywikibot.Page(site, 'Talk:First page')
        p3 = pywikibot.Page(site, 'User:Second page')
        p4 = pywikibot.Page(site, 'User talk:Second page')
        self.assertFalse(p1.isTalkPage())
        self.assertTrue(p2.isTalkPage())
        self.assertFalse(p3.isTalkPage())
        self.assertTrue(p4.isTalkPage())

    def testIsCategory(self):
        """Test is_categorypage method."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'First page')
        p2 = pywikibot.Page(site, 'Category:Second page')
        p3 = pywikibot.Page(site, 'Category talk:Second page')
        self.assertEqual(p1.is_categorypage(), False)
        self.assertEqual(p2.is_categorypage(), True)
        self.assertEqual(p3.is_categorypage(), False)

    def testIsFile(self):
        """Test C{Page.is_filepage} check."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'First page')
        p2 = pywikibot.Page(site, 'File:Second page')
        p3 = pywikibot.Page(site, 'Image talk:Second page')
        self.assertEqual(p1.is_filepage(), False)
        self.assertEqual(p2.is_filepage(), True)
        self.assertEqual(p3.is_filepage(), False)

    def testApiMethods(self):
        """Test various methods that rely on API."""
        mainpage = self.get_mainpage()
        # since there is no way to predict what data the wiki will return,
        # we only check that the returned objects are of correct type.
        self.assertIsInstance(mainpage.get(), str)
        with suppress_warnings(
                r'pywikibot\.page\.BasePage\.latestRevision '
                r'is deprecated[\s\w]+; '
                r'use latest_revision_id instead\.'):
            self.assertIsInstance(mainpage.latestRevision(), int)
        self.assertIsInstance(mainpage.userName(), str)
        self.assertIsInstance(mainpage.isIpEdit(), bool)
        self.assertIsInstance(mainpage.exists(), bool)
        self.assertIsInstance(mainpage.isRedirectPage(), bool)
        self.assertIsInstance(mainpage.isDisambig(), bool)
        self.assertIsInstance(mainpage.has_permission(), bool)
        self.assertIsInstance(mainpage.botMayEdit(), bool)
        self.assertIsInstance(mainpage.editTime(), pywikibot.Timestamp)
        self.assertIsInstance(mainpage.permalink(), str)

    def test_talk_page(self):
        """Test various methods that rely on API: talk page."""
        mainpage = self.get_mainpage()
        maintalk = mainpage.toggleTalkPage()
        if not maintalk.exists():
            self.skipTest("No talk page for {}'s main page"
                          .format(self.get_site()))
        self.assertIsInstance(maintalk.get(get_redirect=True), str)
        self.assertEqual(mainpage.toggleTalkPage(), maintalk)
        self.assertEqual(maintalk.toggleTalkPage(), mainpage)

    def test_bad_page(self):
        """Test various methods that rely on API: bad page."""
        badpage = self.get_missing_article()
        self.assertRaisesRegex(pywikibot.NoPage, NO_PAGE_RE, badpage.get)

    def testIsDisambig(self):
        """Test the integration with Extension:Disambiguator."""
        site = self.get_site()
        if not site.has_extension('Disambiguator'):
            self.skipTest('Disambiguator extension not loaded on test site')
        pg = pywikibot.Page(site, 'Random')
        pg._pageprops = {'disambiguation', ''}
        self.assertTrue(pg.isDisambig())
        pg._pageprops = set()
        self.assertFalse(pg.isDisambig())

    def testReferences(self):
        """Test references to a page."""
        mainpage = self.get_mainpage()
        count = 0
        # Ignore redirects for time considerations
        for p in mainpage.getReferences(follow_redirects=False):
            count += 1
            self.assertIsInstance(p, pywikibot.Page)
            if count >= 10:
                break
        count = 0
        for p in mainpage.backlinks(follow_redirects=False):
            count += 1
            self.assertIsInstance(p, pywikibot.Page)
            if count >= 10:
                break
        count = 0
        for p in mainpage.embeddedin():
            count += 1
            self.assertIsInstance(p, pywikibot.Page)
            if count >= 10:
                break

    def testLinks(self):
        """Test the different types of links from a page."""
        mainpage = self.get_mainpage()
        for p in mainpage.linkedPages():
            self.assertIsInstance(p, pywikibot.Page)
        iw = list(mainpage.interwiki(expand=True))
        for p in iw:
            self.assertIsInstance(p, pywikibot.Link)
        for p2 in mainpage.interwiki(expand=False):
            self.assertIsInstance(p2, pywikibot.Link)
            self.assertIn(p2, iw)
        for p in mainpage.langlinks():
            self.assertIsInstance(p, pywikibot.Link)
        for p in mainpage.imagelinks():
            self.assertIsInstance(p, pywikibot.FilePage)
        for p in mainpage.templates():
            self.assertIsInstance(p, pywikibot.Page)
        for t, params in mainpage.templatesWithParams():
            self.assertIsInstance(t, pywikibot.Page)
            self.assertIsInstance(params, list)
        for p in mainpage.categories():
            self.assertIsInstance(p, pywikibot.Category)
        for p in mainpage.extlinks():
            self.assertIsInstance(p, str)

    def testPickleAbility(self):
        """Test the ability to pickle the page."""
        mainpage = self.get_mainpage()
        mainpage_str = pickle.dumps(mainpage, protocol=config.pickle_protocol)
        mainpage_unpickled = pickle.loads(mainpage_str)
        self.assertEqual(mainpage, mainpage_unpickled)

    def test_redirect(self):
        """Test that the redirect option is set correctly."""
        site = self.get_site()
        for page in site.allpages(filterredir=True, total=1):
            break
        else:
            self.skipTest('No redirect pages on site {0!r}'.format(site))
        # This page is already initialised
        self.assertTrue(hasattr(page, '_isredir'))
        # call api.update_page without prop=info
        del page._isredir
        page.isDisambig()
        self.assertTrue(page.isRedirectPage())

        page_copy = pywikibot.Page(site, page.title())
        self.assertFalse(hasattr(page_copy, '_isredir'))
        page_copy.isDisambig()
        self.assertTrue(page_copy.isRedirectPage())

    def test_depth(self):
        """Test page depth calculation."""
        site = self.get_site()
        page_d0 = pywikibot.Page(site, '/home/test/')
        if site.namespaces[0].subpages:
            self.assertEqual(page_d0.depth, 3)
        else:
            self.assertEqual(page_d0.depth, 0)

        page_user_d0 = pywikibot.Page(site, 'User:Sn1per')
        self.assertEqual(page_user_d0.depth, 0)

        page_d3 = pywikibot.Page(site, 'User:Sn1per/ProtectTest1/test/test')
        self.assertEqual(page_d3.depth, 3)

    def test_page_image(self):
        """
        Test C{Page.page_image} function.

        Since we are not sure what the wiki will return, we mainly test types
        """
        site = self.get_site()
        mainpage = self.get_mainpage()
        image = pywikibot.FilePage(site, 'File:Jean-Léon Gérôme 003.jpg')

        if site.mw_version < '1.20':
            self.assertRaises(NotImplementedError, mainpage.page_image)
        elif site.has_extension('PageImages'):
            mainpage_image = mainpage.page_image()
            if mainpage_image is not None:
                self.assertIsInstance(mainpage_image, pywikibot.FilePage)
            # for file pages, the API should return the file itself
            self.assertEqual(image.page_image(), image)
        else:
            self.assertRaisesRegex(pywikibot.UnknownExtension,
                                   'Method "loadpageimage" is not implemented '
                                   'without the extension PageImages',
                                   mainpage.page_image)


class TestPageCoordinates(TestCase):

    """Test Page Object using German Wikipedia."""

    family = 'wikipedia'
    code = 'de'

    cached = True

    def test_coordinates(self):
        """Test C{Page.coodinates} method."""
        page = pywikibot.Page(self.site, 'Berlin')
        with self.subTest(primary_only=False):
            coords = page.coordinates()
            self.assertIsInstance(coords, list)
            for coord in coords:
                self.assertIsInstance(coord, pywikibot.Coordinate)
                self.assertIsInstance(coord.primary, bool)

        with self.subTest(primary_only=True):
            coord = page.coordinates(primary_only=True)
            self.assertIsInstance(coord, pywikibot.Coordinate)
            self.assertTrue(coord.primary)


class TestPageBaseUnicode(DefaultDrySiteTestCase):

    """Base class for tests requiring a page using a unicode title."""

    @classmethod
    def setUpClass(cls):
        """Initialize page instance."""
        super().setUpClass()
        cls.page = pywikibot.Page(cls.site, 'Ō')


class TestPageGetFileHistory(DefaultDrySiteTestCase):

    """Test the get_file_history method of the FilePage class."""

    def test_get_file_history_cache(self):
        """Test the cache mechanism of get_file_history."""
        with mock.patch.object(self.site, 'loadimageinfo', autospec=True):
            page = pywikibot.FilePage(self.site, 'File:Foo.jpg')
            _file_revisions = page.get_file_history()
            # On the first call the history is loaded via API
            self.assertEqual(_file_revisions, {})
            # Fill the cache
            _file_revisions['foo'] = 'bar'
            # On the second call page._file_revisions is returned
            self.assertEqual(page.get_file_history(), {'foo': 'bar'})
            self.site.loadimageinfo.assert_called_once_with(page, history=True)


class TestFilePage(DefaultSiteTestCase):

    """Test methods of the FilePage class."""

    family = 'commons'
    code = 'commons'

    cached = True

    def test_globalusage(self, key):
        """Test globalusage generator."""
        page = pywikibot.FilePage(self.site, 'File:Example.jpg')
        gen = page.globalusage(total=3)
        pages = list(gen)
        self.assertLength(pages, 3)
        self.assertTrue(any(isinstance(p), pywikibot.Page) for p in pages)
        self.assertTrue(any(p.site != self.site for p in pages))


class TestPageRepr(TestPageBaseUnicode):

    """Test for Page's repr implementation."""

    def setUp(self):
        """Force the console encoding to UTF-8."""
        super().setUp()
        self._old_encoding = config.console_encoding
        config.console_encoding = 'utf8'

    def tearDown(self):
        """Restore the original console encoding."""
        config.console_encoding = self._old_encoding
        super().tearDown()

    def test_mainpage_type(self):
        """Test the return type of repr(Page(<main page>)) is str."""
        mainpage = self.get_mainpage()
        self.assertIsInstance(repr(mainpage), str)

    def test_unicode_type(self):
        """Test the return type of repr(Page('<non-ascii>')) is str."""
        page = pywikibot.Page(self.get_site(), 'Ō')
        self.assertIsInstance(repr(page), str)

    def test_unicode_value(self):
        """Test to capture actual Python result pre unicode_literals."""
        self.assertEqual(repr(self.page), "Page('Ō')")
        self.assertEqual('%r' % self.page, "Page('Ō')")
        self.assertEqual('{0!r}'.format(self.page), "Page('Ō')")


class TestPageReprASCII(TestPageBaseUnicode):

    """Test for Page's repr implementation when using ASCII encoding."""

    def setUp(self):
        """Patch the current console encoding to ASCII."""
        super().setUp()
        self._old_encoding = config.console_encoding
        config.console_encoding = 'ascii'

    def tearDown(self):
        """Restore the original console encoding."""
        config.console_encoding = self._old_encoding
        super().tearDown()


class TestPageBotMayEdit(TestCase):

    """Test Page.botMayEdit() method."""

    family = 'wikipedia'
    code = 'en'

    cached = True
    user = True

    def setUp(self):
        """Setup test."""
        super().setUp()
        self.page = pywikibot.Page(self.site,
                                   'not_existent_page_for_pywikibot_tests')
        if self.page.exists():
            self.skipTest(
                'Page {} exists! Change page name in tests/page_tests.py'
                .format(self.page.title()))

    @mock.patch.object(config, 'ignore_bot_templates', False)
    def test_bot_may_edit_nobots(self):
        """Test with {{nobots}} that bot is allowed to edit."""
        self.page._templates = [pywikibot.Page(self.site, 'Template:Nobots')]
        user = self.site.user()

        # Ban all compliant bots (shortcut).
        self.page.text = '{{nobots}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ban all compliant bots not in the list, syntax for de wp.
        self.page.text = '{{nobots|HagermanBot,Werdnabot}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ban all compliant bots not in the list, syntax for de wp.
        self.page.text = '{{nobots|%s, HagermanBot,Werdnabot}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ban all bots, syntax for de wp.
        self.page.text = '{{nobots|all}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Decline wrong nobots parameter
        self.page.text = '{{nobots|allow=%s}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Decline wrong nobots parameter
        self.page.text = '{{nobots|deny=%s}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Decline wrong nobots parameter
        self.page.text = '{{nobots|decline=%s}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Decline empty keyword parameter with nobots
        self.page.text = '{{nobots|with_empty_parameter=}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ignore second parameter
        self.page.text = '{{nobots|%s|MyBot}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ignore second parameter
        self.page.text = '{{nobots|MyBot|%s}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

    @mock.patch.object(config, 'ignore_bot_templates', False)
    def test_bot_may_edit_bots(self):
        """Test with {{bots}} that bot is allowed to edit."""
        self.page._templates = [pywikibot.Page(self.site, 'Template:Bots')]
        user = self.site.user()

        # Allow all bots (shortcut).
        self.page.text = '{{bots}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ban all compliant bots not in the list.
        self.page.text = '{{bots|allow=HagermanBot,Werdnabot}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ban all compliant bots in the list.
        self.page.text = '{{bots|deny=HagermanBot,Werdnabot}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ban all compliant bots not in the list.
        self.page.text = '{{bots|allow=%s, HagermanBot}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ban all compliant bots in the list.
        self.page.text = '{{bots|deny=%s, HagermanBot}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Allow all bots.
        self.page.text = '{{bots|allow=all}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ban all compliant bots.
        self.page.text = '{{bots|allow=none}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Ban all compliant bots.
        self.page.text = '{{bots|deny=all}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertFalse(self.page.botMayEdit())

        # Allow all bots.
        self.page.text = '{{bots|deny=none}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ignore missing named parameter.
        self.page.text = '{{bots|%s}}' % user
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ignore empty keyword parameter with bots
        for param in ('allow', 'deny', 'empty_parameter'):
            self.page.text = '{{bots|%s=}}' % param
            with self.subTest(template=self.page.text, user=user, param=param):
                self.assertTrue(self.page.botMayEdit())

        # Ignore unknown keyword parameter with bots
        self.page.text = '{{bots|with=unknown_parameter}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

        # Ignore unknown empty parameter keyword with bots
        self.page.text = '{{bots|with_empty_parameter=}}'
        with self.subTest(template=self.page.text, user=user):
            self.assertTrue(self.page.botMayEdit())

    @mock.patch.object(config, 'ignore_bot_templates', False)
    def test_bot_may_edit_inuse(self):
        """Test with {{inuse}} that bot is allowed to edit."""
        self.page._templates = [pywikibot.Page(self.site, 'Template:In use')]

        # Ban all users including bots.
        self.page.text = '{{in use}}'
        self.assertFalse(self.page.botMayEdit())


class TestPageHistory(DefaultSiteTestCase):

    """Test history related functionality."""

    cached = True

    def test_revisions(self):
        """Test Page.revisions()."""
        mp = self.get_mainpage()
        revs = mp.revisions()
        revs = iter(revs)  # implicit assertion
        revs = list(revs)
        self.assertGreater(len(revs), 1)

    def test_contributors(self):
        """Test Page.contributors()."""
        mp = self.get_mainpage()
        cnt = mp.contributors()
        self.assertIsInstance(cnt, dict)
        self.assertGreater(len(cnt), 1)

    def test_revision_count(self):
        """Test Page.edit_count()."""
        mp = self.get_mainpage()
        rev_count = len(list(mp.revisions()))
        self.assertEqual(rev_count, mp.revision_count())
        cnt = mp.contributors()
        self.assertEqual(rev_count, sum(cnt.values()))

        user, count = cnt.most_common(1)[0]
        self.assertEqual(mp.revision_count([user]), count)
        self.assertEqual(mp.revision_count(user), count)
        self.assertEqual(mp.revision_count(pywikibot.User(self.site, user)),
                         count)

        top_two = cnt.most_common(2)
        self.assertIsInstance(top_two, list)
        self.assertLength(top_two, 2)
        self.assertIsInstance(top_two[0], tuple)
        self.assertIsInstance(top_two[0][0], str)
        self.assertIsInstance(top_two[0][1], int)
        top_two_usernames = {top_two[0][0], top_two[1][0]}
        self.assertLength(top_two_usernames, 2)
        top_two_counts = ([top_two[0][1], top_two[1][1]])
        top_two_edit_count = mp.revision_count(top_two_usernames)
        self.assertIsInstance(top_two_edit_count, int)
        self.assertEqual(top_two_edit_count, sum(top_two_counts))


class TestPageRedirects(TestCase):

    """
    Test redirects.

    This is using the pages 'User:Legoktm/R1', 'User:Legoktm/R2' and
    'User:Legoktm/R3' on the English Wikipedia. 'R1' is redirecting to 'R2',
    'R2' is a normal page and 'R3' does not exist.
    """

    family = 'wikipedia'
    code = 'en'

    cached = True

    def testIsRedirect(self):
        """Test C{Page.isRedirectPage()} and C{Page.getRedirectTarget}."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Legoktm/R1')
        p2 = pywikibot.Page(site, 'User:Legoktm/R2')
        self.assertTrue(p1.isRedirectPage())
        p3 = p1.getRedirectTarget()
        self.assertEqual(p3, p2)
        self.assertIsInstance(p3, pywikibot.User)

    def testPageGet(self):
        """Test C{Page.get()} on different types of pages."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Legoktm/R2')
        p2 = pywikibot.Page(site, 'User:Legoktm/R1')
        p3 = pywikibot.Page(site, 'User:Legoktm/R3')

        text = ('This page is used in the [[mw:Manual:Pywikipediabot]] '
                'testing suite.')
        self.assertEqual(p1.get(), text)
        self.assertRaisesRegex(pywikibot.exceptions.IsRedirectPage,
                               r'{0} is a redirect page\.'
                               .format(re.escape(str(p2))), p2.get)
        self.assertRaisesRegex(
            pywikibot.exceptions.NoPage, NO_PAGE_RE, p3.get)

    def test_set_redirect_target(self):
        """Test set_redirect_target method."""
        # R1 redirects to R2 and R3 doesn't exist.
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Legoktm/R2')
        p2 = pywikibot.Page(site, 'User:Legoktm/R1')
        p3 = pywikibot.Page(site, 'User:Legoktm/R3')

        text = p2.get(get_redirect=True)
        self.assertRaisesRegex(pywikibot.exceptions.IsNotRedirectPage,
                               r'{0} is not a redirect page\.'
                               .format(re.escape(str(p1))),
                               p1.set_redirect_target, p2)
        self.assertRaisesRegex(pywikibot.exceptions.NoPage, NO_PAGE_RE,
                               p3.set_redirect_target, p2)
        p2.set_redirect_target(p1, save=False)
        self.assertEqual(text, p2.get(get_redirect=True))


class TestPageUserAction(DefaultSiteTestCase):

    """Test page user actions."""

    user = True

    def test_purge(self):
        """Test purging the mainpage."""
        mainpage = self.get_mainpage()
        self.assertIsInstance(mainpage.purge(), bool)
        self.assertEqual(mainpage.purge(),
                         mainpage.purge(forcelinkupdate=None))

    def test_watch(self):
        """Test Page.watch, with and without unwatch enabled."""
        # Note: this test uses the userpage, so that it is unwatched and
        # therefore is not listed by script_tests test_watchlist_simulate.
        userpage = self.get_userpage()
        rv = userpage.watch()
        self.assertIsInstance(rv, bool)
        self.assertTrue(rv)
        rv = userpage.watch(unwatch=True)
        self.assertIsInstance(rv, bool)
        self.assertTrue(rv)


class TestPageDelete(TestCase):

    """Test page delete / undelete actions."""

    family = 'wikipedia'
    code = 'test'

    write = True
    sysop = True

    def test_delete(self):
        """Test the site.delete and site.undelete method."""
        site = self.get_site()
        p = pywikibot.Page(site, 'User:Unicodesnowman/DeleteTest')
        # Ensure the page exists
        p.text = 'pywikibot unit test page'
        p.save('#redirect[[unit test]]', botflag=True)
        self.assertEqual(p.isRedirectPage(), True)
        # Test deletion
        p.delete(reason='pywikibot unit test', prompt=False, mark=False)
        self.assertEqual(p._pageid, 0)
        self.assertEqual(p.isRedirectPage(), False)
        self.assertRaisesRegex(pywikibot.NoPage,
                               NO_PAGE_RE, p.get, force=True)
        # Test undeleting last two revisions
        del_revs = list(p.loadDeletedRevisions())
        revid = p.getDeletedRevision(del_revs[-1])['revid']
        p.markDeletedRevision(del_revs[-1])
        p.markDeletedRevision(del_revs[-2])
        self.assertRaisesRegex(ValueError, 'is not a deleted revision',
                               p.markDeletedRevision, 123)
        p.undelete(reason='pywikibot unit test')
        revs = list(p.revisions())
        self.assertLength(revs, 2)
        self.assertEqual(revs[1].revid, revid)


class TestApplicablePageProtections(TestCase):

    """Test applicable restriction types."""

    family = 'wikipedia'
    code = 'test'

    def test_applicable_protections(self):
        """Test Page.applicable_protections."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Unicodesnowman/NonexistentPage')
        p2 = pywikibot.Page(site, 'User:Unicodesnowman/ProtectTest')
        p3 = pywikibot.Page(site, 'File:Wiki.png')

        # from the API, since 1.25wmf14
        pp1 = p1.applicable_protections()
        pp2 = p2.applicable_protections()
        pp3 = p3.applicable_protections()

        self.assertEqual(pp1, {'create'})
        self.assertIn('edit', pp2)
        self.assertNotIn('create', pp2)
        self.assertNotIn('upload', pp2)
        self.assertIn('upload', pp3)

        # inferred
        site.version = lambda: '1.24'
        self.assertEqual(pp1, p1.applicable_protections())
        self.assertEqual(pp2, p2.applicable_protections())
        self.assertEqual(pp3, p3.applicable_protections())


class TestPageProtect(TestCase):

    """Test page protect / unprotect actions."""

    family = 'wikipedia'
    code = 'test'

    write = True
    sysop = True

    def test_protect(self):
        """Test Page.protect."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Unicodesnowman/ProtectTest')

        p1.protect(protections={'edit': 'sysop', 'move': 'autoconfirmed'},
                   reason='Pywikibot unit test')
        self.assertEqual(p1.protection(),
                         {'edit': ('sysop', 'infinity'),
                          'move': ('autoconfirmed', 'infinity')})

        p1.protect(protections={'edit': '', 'move': ''},
                   reason='Pywikibot unit test')
        self.assertEqual(p1.protection(), {})

    def test_protect_with_empty_parameters(self):
        """Test Page.protect."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Unicodesnowman/ProtectTest')

        p1.protect(protections={'edit': 'sysop', 'move': 'autoconfirmed'},
                   reason='Pywikibot unit test')
        self.assertEqual(p1.protection(),
                         {'edit': ('sysop', 'infinity'),
                          'move': ('autoconfirmed', 'infinity')})

        p1.protect(reason='Pywikibot unit test')
        self.assertEqual(p1.protection(), {})

    def test_protect_alt(self):
        """Test of Page.protect that works around T78522."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Unicodesnowman/ProtectTest')

        p1.protect(protections={'edit': 'sysop', 'move': 'autoconfirmed'},
                   reason='Pywikibot unit test')
        self.assertEqual(p1.protection(),
                         {'edit': ('sysop', 'infinity'),
                          'move': ('autoconfirmed', 'infinity')})
        # workaround
        p1 = pywikibot.Page(site, 'User:Unicodesnowman/ProtectTest')
        p1.protect(protections={'edit': '', 'move': ''},
                   reason='Pywikibot unit test')
        self.assertEqual(p1.protection(), {})


class HtmlEntity(TestCase):

    """Test that HTML entities are correctly decoded."""

    net = False

    def test_no_entities(self):
        """Test that text is left unchanged."""
        self.assertEqual(pywikibot.page.html2unicode('foobar'), 'foobar')
        self.assertEqual(pywikibot.page.html2unicode(' '), ' ')

    def test_valid_entities(self):
        """Test valid entities."""
        self.assertEqual(pywikibot.page.html2unicode('A&amp;O'), 'A&O')
        self.assertEqual(pywikibot.page.html2unicode('&#x70;&#x79;'), 'py')
        self.assertEqual(pywikibot.page.html2unicode('&#x10000;'),
                         '\U00010000')
        self.assertEqual(pywikibot.page.html2unicode('&#x70;&amp;&#x79;'),
                         'p&y')
        self.assertEqual(pywikibot.page.html2unicode('&#128;'), '€')

    def test_ignore_entities(self):
        """Test ignore entities."""
        self.assertEqual(pywikibot.page.html2unicode('A&amp;O', [38]),
                         'A&amp;O')
        self.assertEqual(pywikibot.page.html2unicode('A&#38;O', [38]),
                         'A&#38;O')
        self.assertEqual(pywikibot.page.html2unicode('A&#x26;O', [38]),
                         'A&#x26;O')
        self.assertEqual(pywikibot.page.html2unicode('A&amp;O', [37]), 'A&O')
        self.assertEqual(pywikibot.page.html2unicode('&#128;', [128]),
                         '&#128;')
        self.assertEqual(pywikibot.page.html2unicode('&#128;', [8364]),
                         '&#128;')
        self.assertEqual(pywikibot.page.html2unicode('&#129;&#141;&#157'),
                         '&#129;&#141;&#157')

    def test_recursive_entities(self):
        """Test recursive entities."""
        self.assertEqual(pywikibot.page.html2unicode('A&amp;amp;O'), 'A&amp;O')

    def test_invalid_entities(self):
        """Test texts with invalid entities."""
        self.assertEqual(pywikibot.page.html2unicode('A&notaname;O'),
                         'A&notaname;O')
        self.assertEqual(pywikibot.page.html2unicode('A&#7f;O'), 'A&#7f;O')
        self.assertEqual(pywikibot.page.html2unicode('&#7f'), '&#7f')
        self.assertEqual(pywikibot.page.html2unicode('&#x70&#x79;'), '&#x70y')


class TestPermalink(TestCase):
    """Test that permalink links are correct."""

    family = 'wikipedia'
    code = 'test'

    def test_permalink(self):
        """Test permalink function."""
        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Framawiki/pwb_tests/permalink')
        self.assertEqual(p1.permalink(),
                         '//test.wikipedia.org/w/index.php?title=User%3A'
                         'Framawiki%2Fpwb_tests%2Fpermalink&oldid=340685')
        self.assertEqual(p1.permalink(oldid='340684'),
                         '//test.wikipedia.org/w/index.php?title=User%3A'
                         'Framawiki%2Fpwb_tests%2Fpermalink&oldid=340684')
        self.assertEqual(p1.permalink(percent_encoded=False),
                         '//test.wikipedia.org/w/index.php?title=User:'
                         'Framawiki/pwb_tests/permalink&oldid=340685')
        self.assertEqual(p1.permalink(with_protocol=True),
                         'https://test.wikipedia.org/w/index.php?title=User%3A'
                         'Framawiki%2Fpwb_tests%2Fpermalink&oldid=340685')


class TestShortLink(TestCase):
    """Test that short link management is correct."""

    user = True

    family = 'wikipedia'
    code = 'test'

    def test_create_short_link(self):
        """Test create_short_link function."""
        # Make sure test user is logged in on meta:meta (T244062)
        meta = pywikibot.Site('meta', 'meta')
        if not meta.logged_in():
            meta.login()

        site = self.get_site()
        p1 = pywikibot.Page(site, 'User:Framawiki/pwb_tests/shortlink')
        with self.subTest(parameters='defaulted'):
            self.assertEqual(p1.create_short_link(), 'https://w.wiki/3Cy')
        with self.subTest(with_protocol=True):
            self.assertEqual(p1.create_short_link(with_protocol=True),
                             'https://w.wiki/3Cy')
        with self.subTest(permalink=True):
            self.assertEqual(p1.create_short_link(permalink=True,
                                                  with_protocol=False),
                             'w.wiki/3Cz')


if __name__ == '__main__':  # pragma: no cover
    with suppress(SystemExit):
        unittest.main()
