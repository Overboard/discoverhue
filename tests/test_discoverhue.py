""" Test suite for discoverhue """

# TODO: consolidate scenario data
# by creating a comprehensive mock for from_url
import doctest
import unittest
from unittest.mock import patch, Mock
import pickle

from discoverhue.discoverhue import *

PATH = "tests\\"

class Desalinator(pickle.Unpickler):
    """ Restricted class unpickler """
    _whitelisted_classes = {
        ('ssdp', 'SSDPResponse')
    }

    def find_class(self, module, name):
        print('Decoding {}.{}'.format(module, name))
        if (module, name) in self._whitelisted_classes:
            # FIXME: grr, namespace
            return super().find_class('discoverhue.'+module, name)
        else:
            raise pickle.UnpicklingError("global '%s.%s' is forbidden" %
                                         (module, name))
        # import importlib
        # mod = importlib.import_module(module)
        # return getattr(mod, name)

def get_ssdp_scenario(filename):
    """ Load a saved test scenario """
    with open(PATH+filename, 'rb') as f:
        page = Desalinator(f).load()
    return page

def get_http_scenario(filename):
    """ Load a saved xml scenario """
    with open(PATH+filename, 'rb') as f:
        page = f.read().decode()
    return page

#-----------------------------------------------------------------------------
# parse_description_xml
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.logging.info', return_value='')
# TODO: could use with/assertLogs instead
class TestParseDescriptionXML(unittest.TestCase):
    """ Unit tests for the parse_description_xml

    Mocks required for 'from_url' and logging
    """
    parsed_xml_response = [
        (None, None),
        ('001788102201', Bridge(ip='http://192.168.1.130:80/',
            icon='hue_logo_0.png', user=None)),
        ('0017884e7dad', Bridge(ip='http://192.168.0.23:80/',
            icon='hue_logo_0.png', user=None))
    ]

    @patch('discoverhue.discoverhue.from_url', side_effect=ValueError)
    def test_malformed_url(self, url_mock, log_mock):
        """ Expect a badly formed url argument to pass back the exception
        from urllib.requests
        """
        with self.assertRaises(ValueError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.URLError(''))
    def test_nonexistent_ip(self, url_mock, log_mock):
        """ Expect an unreachable ip to log message and continue
        """
        parse_description_xml('location')
        self.assertEqual(log_mock.call_count, 1)

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.HTTPError('', '', '', '', ''))
    def test_no_file_at_ip(self, url_mock, log_mock):
        """ Expect an ip with no description.xml to log message and continue
        """
        parse_description_xml('location')
        self.assertEqual(log_mock.call_count, 1)

    @patch('discoverhue.discoverhue.from_url', return_value='<root></notroot>')
    def test_bad_xml(self, url_mock, log_mock):
        """ Expect malformed xml to raise ParseError
        """
        import xml.etree.ElementTree
        with self.assertRaises(xml.etree.ElementTree.ParseError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('00_description.xml'))
    def test_missing_data_in_xml(self, url_mock, log_mock):
        """ Expect xml with missing data to raise AttributeError
        """
        with self.assertRaises(AttributeError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('01_description.xml'))
    def test_example_xml(self, url_mock, log_mock):
        """ Expect results from provided example
        """
        results = (parse_description_xml('location'))
        self.assertEqual(results, self.parsed_xml_response[1])

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('02_description.xml'))
    def test_local_xml(self, url_mock, log_mock):
        """ Expect results from local example
        """
        results = (parse_description_xml('location'))
        self.assertEqual(results, self.parsed_xml_response[2])


#-----------------------------------------------------------------------------
# parse_portal_json
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.logging.warning', return_value='')
# TODO: could use with/assertLogs instead
class TestParsePortalJSON(unittest.TestCase):
    """ Unit tests for the parse_portal_json

    Mocks required for 'from_url' and logging
    """
    parsed_portal_response = [
        ("001788fffe100491", "http://192.168.2.23/description.xml"),
        ("001788fffe09a168", "http://192.168.88.252/description.xml"),
        ("001788fffe16c18f", "http://192.168.2.20/description.xml"),
        ("001788fffe4e7dad", "http://192.168.0.23/description.xml")
    ]

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.URLError(''))
    def test_nonexistent_portal(self, url_mock, log_mock):
        """ Expect an unreachable ip to log message and continue
        """
        parse_portal_json()
        self.assertEqual(log_mock.call_count, 1)

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.HTTPError('', '', '', '', ''))
    def test_no_json_at_ip(self, url_mock, log_mock):
        """ Expect to re-raise an HTTPError presumbaly something changed at portal
        """
        with self.assertRaises(urllib.request.HTTPError):
            parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value='{/}')
    def test_bad_json(self, url_mock, log_mock):
        """ Expect malformed JSON to raise json.decoder.JSONDecodeError
        """
        with self.assertRaises(json.decoder.JSONDecodeError):
            results = parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('00_portal.json'))
    def test_missing_data_in_json(self, url_mock, log_mock):
        """ Expect missing data to raise KeyError
        """
        with self.assertRaises(KeyError):
            results = parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('01_portal.json'))
    def test_example_json(self, url_mock, log_mock):
        """ Expect results from provided example
        """
        results = parse_portal_json()
        self.assertEqual(results, self.parsed_portal_response[0:3])

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('02_portal.json'))
    def test_local_json(self, url_mock, log_mock):
        """ Expect results from local example
        """
        results = parse_portal_json()
        self.assertEqual(len(results),1)
        self.assertEqual(results, self.parsed_portal_response[3:4])

#-----------------------------------------------------------------------------
# via_upnp
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.from_url', return_value='')
class TestUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for SSDP discovery response and XML request
    TODO: the from_url mock is no longer necessary for this test
    """

    def setUp(self):
        self.mock_xml = Mock(return_value=('0017884e7dad',
            Bridge(ip='http://192.168.0.23:80/', icon='hue_logo_0.png', user=None)))
        self.patcher = patch('discoverhue.discoverhue.parse_description_xml', self.mock_xml)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_1in4.pickle'))
    def test_1in4(self, poll_mock, url_mock):
        """ SSDP returns 4 devices with one being a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(self.mock_xml.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_1in1.pickle'))
    def test_1in1(self, poll_mock, url_mock):
        """ SSDP returns one device, a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(self.mock_xml.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_0in3.pickle'))
    def test_0in3(self, poll_mock, url_mock):
        """ SSDP returns three devices, no bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 0)
        self.mock_xml.assert_not_called()


#-----------------------------------------------------------------------------
# via_nupnp
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.from_url', return_value='')
class TestNUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for portal response and XML request
    TODO: the from_url mock is no longer necessary for this test
    """
    parsed_portal_response = [
        ("001788fffe100491", "http://192.168.2.23/description.xml"),
        ("001788fffe09a168", "http://192.168.88.252/description.xml"),
        ("001788fffe16c18f", "http://192.168.2.20/description.xml"),
        ("001788fffe4e7dad", "http://192.168.0.23/description.xml")
    ]

    parsed_xml_response = [
        (None, None),
        (None, None),
        (None, None),
        ('0017884e7dad', Bridge(ip='http://192.168.0.23:80/',
            icon='hue_logo_0.png', user=None))
    ]

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response)
    @patch('discoverhue.discoverhue.parse_description_xml', side_effect=parsed_xml_response)
    def test_1in4(self, xml_mock, json_mock, url_mock):
        """ Portal returns 4 devices with one being a bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 4)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response[3:4])
    @patch('discoverhue.discoverhue.parse_description_xml', side_effect=parsed_xml_response[3:4])
    def test_1in1(self, xml_mock, json_mock, url_mock):
        """ Portal returns one device, a bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 1)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response[0:3])
    @patch('discoverhue.discoverhue.parse_description_xml', side_effect=parsed_xml_response[0:3])
    def test_0in3(self, xml_mock, json_mock, url_mock):
        """ Portal returns three devices, no bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 3)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 0)

# doctest integration
# def load_tests(loader, tests, ignore):
#     import discoverhue
#     tests.addTests(doctest.DocTestSuite(discoverhue))
#     return tests

if __name__ == '__main__':
    unittest.main()
