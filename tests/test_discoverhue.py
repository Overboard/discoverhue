""" Test suite for discoverhue """
# import doctest
import unittest
from unittest.mock import patch
import pickle

from discoverhue.discoverhue import *

PATH = "tests\\"
HARG = ('', '', '', '', '')

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
# Mocked Network Environment
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
"""
In this simulated network environment:

SSDP will return the following locations via SSDP_1in4.pickle:
    http://192.168.0.26:49152/0/description.xml
    http://192.168.0.25:8089/
    http://192.168.0.23:80/description.xml
    http://192.168.0.26:49152/2/description.xml

    where only the third item is an IpBridge

The portal will return:
    [{
        "id":"001788fffe100491",
        "internalipaddress":"192.168.2.23",
        "macaddress":"00:17:88:10:04:91",
        "name":"Philips Hue"
    },
    {
        "id":"001788fffe09a168",
        "internalipaddress":"192.168.88.252"
    },
    {
        "id":"001788fffe16c18f",
        "internalipaddress":"192.168.2.20",
        "macaddress":"00:17:88:16:c1:8f",
        "name":"Philips Hue"
    },
    {
        "id":"001788fffe4e7dad",
        "internalipaddress":"192.168.0.23"
    }]

    where only the last is reachable

TODO: rename tests
"""
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

def from_url_mock(location):
    """ Mock for 'from_url' """
    try:
        exec(url_dispatch[location])
        return eval('page')
    except KeyError:
        # Missing test case, treat same as unreachable IP
        raise urllib.request.URLError("No mock dispatch")

def parse_description_xml_mock(location):
    """ Mock for 'parse_description_xml' """
    try:
        return parsed_xml_response[location]
    except KeyError:
        # Missing test case, treat as unreachable IP
        return None, urllib.request.URLError(location)
        # TODO: remove ?
        # Missing test case, treat as test module error
        # raise Exception('Missing lookup for test')

url_dispatch = {
    'http://192.168.0.26:49152/0/description.xml':
        'raise urllib.request.URLError("")',    # TODO: change to wrong XML
    'http://192.168.0.26:49152/2/description.xml':
        'raise urllib.request.URLError("")',    # TODO: change to wrong XML
    'http://192.168.0.25:8089/':
        'raise urllib.request.HTTPError(*HARG)',
    'http://192.168.1.130:80/description.xml':
        'page = get_http_scenario("01_description.xml")',
    'http://192.168.0.23:80/description.xml':
        'page = get_http_scenario("02_description.xml")',
    None:
        'raise ValueError'
}

# Note: SSDP returns the port number in the URL, while the Portal does not
# hence the duplicate entries below to satisfy the test lookups
parsed_xml_response = {
    'http://192.168.1.130:80/description.xml':
        ('001788102201', 'http://192.168.1.130:80/'),
    'http://192.168.0.23:80/description.xml':
        ('0017884e7dad', 'http://192.168.0.23:80/'),
    'http://192.168.1.130/description.xml':
        ('001788102201', 'http://192.168.1.130:80/'),
    'http://192.168.0.23/description.xml':
        ('0017884e7dad', 'http://192.168.0.23:80/'),
    'http://192.168.88.252/description.xml':
        (None, None),
    'http://192.168.2.20/description.xml':
        (None, None),
    'http://192.168.2.23/description.xml':
        (None, None),
}

parsed_portal_response = [
    ("001788fffe100491", "http://192.168.2.23/description.xml"),
    ("001788fffe09a168", "http://192.168.88.252/description.xml"),
    ("001788fffe16c18f", "http://192.168.2.20/description.xml"),
    ("001788fffe4e7dad", "http://192.168.0.23/description.xml"),
    ("001788fffe102201", "http://192.168.1.130/description.xml")
]

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
# Unit tests
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# parse_description_xml
#-----------------------------------------------------------------------------
class TestParseDescriptionXML(unittest.TestCase):
    """ Unit tests for the parse_description_xml

    Mock required for 'from_url'
    """

    @patch('discoverhue.discoverhue.from_url', side_effect=ValueError)
    def test_malformed_url(self, url_mock):
        """ Expect a badly formed url argument to pass back the exception
        from urllib.requests
        """
        with self.assertRaises(ValueError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', side_effect=ValueError)
    def test_none(self, url_mock):
        """ Expect None to pass back the exception from urllib.requests
        """
        with self.assertRaises(ValueError):
            parse_description_xml(None)

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.URLError(''))
    def test_nonexistent_ip(self, url_mock):
        """ Expect an unreachable ip to log message and continue
        """
        with self.assertLogs(level='INFO'):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.HTTPError(*HARG))
    def test_no_file_at_ip(self, url_mock):
        """ Expect an ip with no description.xml to log message and continue
        """
        with self.assertLogs(level='INFO'):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', return_value='<root></notroot>')
    def test_bad_xml(self, url_mock):
        """ Expect malformed xml to raise ParseError
        """
        import xml.etree.ElementTree
        with self.assertRaises(xml.etree.ElementTree.ParseError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('00_description.xml'))
    def test_missing_data_in_xml(self, url_mock):
        """ Expect xml with missing data to raise AttributeError
        """
        with self.assertRaises(AttributeError):
            parse_description_xml('location')

    @patch('discoverhue.discoverhue.from_url', side_effect=from_url_mock)
    def test_example_xml(self, url_mock):
        """ Expect results from provided example
        """
        location = 'http://192.168.1.130:80/description.xml'
        results = (parse_description_xml(location))
        self.assertEqual(results, parsed_xml_response[location])

    @patch('discoverhue.discoverhue.from_url', side_effect=from_url_mock)
    def test_local_xml(self, url_mock):
        """ Expect results from local example
        """
        location = 'http://192.168.0.23:80/description.xml'
        results = (parse_description_xml(location))
        self.assertEqual(results, parsed_xml_response[location])


#-----------------------------------------------------------------------------
# parse_portal_json
#-----------------------------------------------------------------------------
class TestParsePortalJSON(unittest.TestCase):
    """ Unit tests for the parse_portal_json

    Mocks required for 'from_url'
    """

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.URLError(''))
    def test_nonexistent_portal(self, url_mock):
        """ Expect an unreachable ip to log message and continue
        """
        with self.assertLogs(level='WARN'):
            parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', side_effect=urllib.request.HTTPError(*HARG))
    def test_no_json_at_ip(self, url_mock):
        """ Expect to re-raise an HTTPError presumably something changed at portal
        """
        with self.assertRaises(urllib.request.HTTPError):
            parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value='{/}')
    def test_bad_json(self, url_mock):
        """ Expect malformed JSON to raise json.decoder.JSONDecodeError
        """
        with self.assertRaises(json.decoder.JSONDecodeError):
            results = parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('00_portal.json'))
    def test_missing_data_in_json(self, url_mock):
        """ Expect missing data to raise KeyError
        """
        with self.assertRaises(KeyError):
            results = parse_portal_json()

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('01_portal.json'))
    def test_example_json(self, url_mock):
        """ Expect results from provided example
        """
        results = parse_portal_json()
        self.assertEqual(results, parsed_portal_response[0:3])

    @patch('discoverhue.discoverhue.from_url', return_value=get_http_scenario('02_portal.json'))
    def test_local_json(self, url_mock):
        """ Expect results from local example
        """
        results = parse_portal_json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results, parsed_portal_response[3:4])

    def test_build_from(self):
        """ Arguably overboard on future proofing """
        from discoverhue.discoverhue import _build_from
        args = [
            ('192.168.0.16', 'http://192.168.0.16/description.xml'),
            ('192.168.0.16/', 'http://192.168.0.16/description.xml'),
            ('//192.168.0.16', 'http://192.168.0.16/description.xml'),
            ('//192.168.0.16/', 'http://192.168.0.16/description.xml'),
            ('http://192.168.0.16', 'http://192.168.0.16/description.xml'),
            ('http://192.168.0.16/', 'http://192.168.0.16/description.xml'),
            ('HTTP://192.168.0.16', 'http://192.168.0.16/description.xml'),
            ('https://192.168.0.16', 'https://192.168.0.16/description.xml'),

            ('192.168.0.16:80', 'http://192.168.0.16:80/description.xml'),
            ('192.168.0.16:80/', 'http://192.168.0.16:80/description.xml'),
            ('http://192.168.0.16:80', 'http://192.168.0.16:80/description.xml'),
            ('http://192.168.0.16:80/', 'http://192.168.0.16:80/description.xml'),

            ('192.168.0.16/path', 'http://192.168.0.16/path/description.xml'),
            ('192.168.0.16/path/', 'http://192.168.0.16/path/description.xml'),
            ('http://192.168.0.16/path', 'http://192.168.0.16/path/description.xml'),
            ('http://192.168.0.16/path/', 'http://192.168.0.16/path/description.xml'),

            ('192.168.0.16:80/path', 'http://192.168.0.16:80/path/description.xml'),
            ('192.168.0.16:80/path/', 'http://192.168.0.16:80/path/description.xml'),
            ('http://192.168.0.16:80/path', 'http://192.168.0.16:80/path/description.xml'),
            ('http://192.168.0.16:80/path/', 'http://192.168.0.16:80/path/description.xml'),

            ('192.168.0.16/description.xml', 'http://192.168.0.16/description.xml'),
            ('//192.168.0.16/description.xml', 'http://192.168.0.16/description.xml'),
            ('http://192.168.0.16/description.xml', 'http://192.168.0.16/description.xml'),
            ('https://192.168.0.16/description.xml', 'https://192.168.0.16/description.xml'),

            ('192.168.0.16:80/description.xml', 'http://192.168.0.16:80/description.xml'),
            ('//192.168.0.16:80/description.xml', 'http://192.168.0.16:80/description.xml'),
            ('http://192.168.0.16:80/description.xml', 'http://192.168.0.16:80/description.xml'),
            ('https://192.168.0.16:80/description.xml', 'https://192.168.0.16:80/description.xml'),

            ('192.168.0.16/path/description.xml', 'http://192.168.0.16/path/description.xml'),
            ('//192.168.0.16/path/description.xml', 'http://192.168.0.16/path/description.xml'),
            ('http://192.168.0.16/path/description.xml', 'http://192.168.0.16/path/description.xml'),
            ('https://192.168.0.16/path/description.xml', 'https://192.168.0.16/path/description.xml'),

            ('192.168.0.16:80/path/description.xml', 'http://192.168.0.16:80/path/description.xml'),
            ('//192.168.0.16:80/path/description.xml', 'http://192.168.0.16:80/path/description.xml'),
            ('http://192.168.0.16:80/path/description.xml', 'http://192.168.0.16:80/path/description.xml'),
            ('https://192.168.0.16:80/path/description.xml', 'https://192.168.0.16:80/path/description.xml'),
        ]
        logging.disable(logging.CRITICAL)
        for arg, res in args:
            xmlurl = _build_from(arg)
            self.assertEqual(xmlurl, res, msg="arg was {}".format(arg))
        logging.disable(logging.NOTSET)


#-----------------------------------------------------------------------------
# via_upnp
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.parse_description_xml', side_effect=parse_description_xml_mock)
class TestUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for SSDP discovery response and XML request
    """

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_1in4.pickle'))
    def test_1in4(self, poll_mock, xml_mock):
        """ SSDP returns 4 devices with one being a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(xml_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_1in1.pickle'))
    def test_1in1(self, poll_mock, xml_mock):
        """ SSDP returns one device, a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(xml_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_0in3.pickle'))
    def test_0in3_upnp(self, poll_mock, xml_mock):
        """ SSDP returns three devices, no bridge """
        with self.assertRaises(DiscoveryError):
            found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        # self.assertEqual(len(found_bridges), 0)
        xml_mock.assert_not_called()


#-----------------------------------------------------------------------------
# via_nupnp
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.parse_description_xml', side_effect=parse_description_xml_mock)
class TestNUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for portal response and XML request
    """
    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response)
    def test_2in5(self, json_mock, xml_mock):
        """ Portal returns 4 devices with one being a bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 5)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 2)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response[0:4])
    def test_1in4(self, json_mock, xml_mock):
        """ Portal returns 4 devices with one being a bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 4)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response[3:4])
    def test_1in1(self, json_mock, xml_mock):
        """ Portal returns one device, a bridge """
        found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 1)
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response[0:3])
    def test_0in3_nupnp(self, json_mock, xml_mock):
        """ Portal returns three devices, no bridge """
        with self.assertRaises(DiscoveryError):
            found_bridges = via_nupnp()
        self.assertEqual(xml_mock.call_count, 3)
        self.assertEqual(json_mock.call_count, 1)
        # self.assertEqual(len(found_bridges), 0)


#-----------------------------------------------------------------------------
# find_bridges
#-----------------------------------------------------------------------------
@patch('discoverhue.discoverhue.parse_description_xml', side_effect=parse_description_xml_mock)
# @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_ssdp_scenario('SSDP_1in4.pickle'))
@patch('discoverhue.discoverhue.ssdp_discover', return_value=[])
@patch('discoverhue.discoverhue.parse_portal_json', return_value=parsed_portal_response)
class TestFindBridges(unittest.TestCase):
    """ Unit tests for find_bridges entry point

    Mocks for ssdp, portal, and xml
    Simulate ssdp failover to portal, yielding 2 bridges reachable with xml
    """

    def test_find_bridges_01(self, json_mock, poll_mock, xml_mock):
        """ with no parameters expect return of dict with two bridges """
        found_bridges = find_bridges()
        # confirm mock calls
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(xml_mock.call_count, 5)
        # confirm results
        self.assertEqual(len(found_bridges), 2)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'], 'http://192.168.0.23:80/')

    def test_find_bridges_02(self, json_mock, poll_mock, xml_mock):
        """ with good serial number expect return of string with ip """
        found_bridges = find_bridges('0017884e7dad')
        self.assertEqual(found_bridges, 'http://192.168.0.23:80/')
        found_bridges = find_bridges('001788102201')
        self.assertEqual(found_bridges, 'http://192.168.1.130:80/')

    def test_find_bridges_03(self, json_mock, poll_mock, xml_mock):
        """ with missing serial expect return of none """
        found_bridges = find_bridges('deadbeef')
        self.assertEqual(found_bridges, None)

    def test_find_bridges_04(self, json_mock, poll_mock, xml_mock):
        """ with non-hashable input expect same as None """
        found_bridges = find_bridges(['deadbeef', '0017884e7dad'])
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 2)

    @unittest.expectedFailure
    def test_find_bridges_05(self, json_mock, poll_mock, xml_mock):
        """ with empty non-hashable input expect same as None """
        found_bridges = find_bridges({})
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 2)
        print(found_bridges)

    def test_find_bridges_06(self, json_mock, poll_mock, xml_mock):
        """ with good bridge expect no discovery """
        known_bridges = {'0017884e7dad': 'http://192.168.0.23:80/'}
        found_bridges = find_bridges(known_bridges)
        # confirm mock calls
        self.assertEqual(json_mock.call_count, 0)
        self.assertEqual(poll_mock.call_count, 0)
        self.assertEqual(xml_mock.call_count, 1)
        # confirm results
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 1)
        self.assertEqual(len(known_bridges), 0)

    def test_find_bridges_07(self, json_mock, poll_mock, xml_mock):
        """ with two good bridges expect no discovery """
        known_bridges = {
            '0017884e7dad': 'http://192.168.0.23:80/',
            '001788102201': 'http://192.168.1.130:80/',
        }
        found_bridges = find_bridges(known_bridges)
        # confirm mock calls
        self.assertEqual(json_mock.call_count, 0)
        self.assertEqual(poll_mock.call_count, 0)
        self.assertEqual(xml_mock.call_count, 2)
        # confirm results
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 2)
        self.assertEqual(len(known_bridges), 0)

    def test_find_bridges_08(self, json_mock, poll_mock, xml_mock):
        """ with two good bridges expect no discovery """
        known_bridges = {
            '0017884e7dad': 'http://192.168.0.23:80/', 
            '001788102201': 'http://192.168.1.130:80/',
            
        }
        found_bridges = find_bridges(known_bridges)
        # confirm mock calls
        self.assertEqual(json_mock.call_count, 0)
        self.assertEqual(poll_mock.call_count, 0)
        self.assertEqual(xml_mock.call_count, 2)
        # confirm results
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 2)
        self.assertEqual(len(known_bridges), 0)
        print(known_bridges, found_bridges)

    def test_find_bridges_09(self, json_mock, poll_mock, xml_mock):
        """ with two good, one bad bridges expect discovery """
        known_bridges = {
            '0017884e7dad': 'http://192.168.0.23:80/',
            '001788102201': 'http://192.168.1.130:80/',
            '00deadbeef00': 'http://192.168.2.20/',
        }
        found_bridges = find_bridges(known_bridges)
        # confirm mock calls
        self.assertEqual(json_mock.call_count, 1)
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(xml_mock.call_count, 8)
        # confirm results
        self.assertIsInstance(found_bridges, dict)
        self.assertEqual(len(found_bridges), 2)
        self.assertEqual(len(known_bridges), 1)
        print(known_bridges, found_bridges)

# doctest integration
# def load_tests(loader, tests, ignore):
#     import discoverhue
#     tests.addTests(doctest.DocTestSuite(discoverhue))
#     return tests

if __name__ == '__main__':
    unittest.main()
