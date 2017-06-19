""" Test suite for discoverhue """
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

def get_scenario(filename):
    """ Load a saved test scenario """
    with open(PATH+filename, 'rb') as f:
        page = Desalinator(f).load()
    return page

@patch('discoverhue.discoverhue.from_url', return_value='')
class TestUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for SSDP discovery response and XML request
    """

    def setUp(self):
        self.mock_xml = Mock(return_value=('0017884e7dad',
            Bridge(ip='http://192.168.0.23:80/', icon='hue_logo_0.png', user=None)))
        self.patcher = patch('discoverhue.discoverhue.parse_description_xml', self.mock_xml)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_scenario('SSDP_1in4.pickle'))
    def test_1in4(self, poll_mock, url_mock):
        """ SSDP returns 4 devices with one being a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(self.mock_xml.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_scenario('SSDP_1in1.pickle'))
    def test_1in1(self, poll_mock, url_mock):
        """ SSDP returns one device, a bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(self.mock_xml.call_count, 1)
        self.assertEqual(len(found_bridges), 1)
        self.assertIn('0017884e7dad', found_bridges)
        self.assertEqual(found_bridges['0017884e7dad'].ip, 'http://192.168.0.23:80/')

    @patch('discoverhue.discoverhue.ssdp_discover', return_value=get_scenario('SSDP_0in3.pickle'))
    def test_0in3(self, poll_mock, url_mock):
        """ SSDP returns three devices, no bridge """
        found_bridges = via_upnp()
        self.assertEqual(poll_mock.call_count, 1)
        self.assertEqual(len(found_bridges), 0)
        self.mock_xml.assert_not_called()



@patch('discoverhue.discoverhue.from_url', return_value='')
class TestNUPNPdiscovery(unittest.TestCase):
    """ Unit tests for the UPnP method

    Mocks required for portal response and XML request
    """
    parsed_portal_response = [
        ("001788fffe100491", "http://192.168.2.23"),
        ("001788fffe09a168", "http://192.168.88.252"),
        ("001788fffe16c18f", "http://192.168.2.20"),
        ("001788fffe4e7dad", "http://192.168.0.23")
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
