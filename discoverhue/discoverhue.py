""" Auto discovery of Hue bridges

Implements UPnP, N-PnP, and ?Manual? methods.
Does not implement IP Scan.

Reference:
https://developers.meethue.com/documentation/hue-bridge-discovery

SSDP response will have a location such as
http://192.168.0.???:80/description.xml

TODO: update text
Outline:
Enter discovery with bridge dict and create bool + user name
    Check for bridges at provided IP's
    Run discovery if not all ID's have a valid IP
    Discovery:
        if running upnp finds nothing,
            if running n-upnp finds nothing,
                if running ip scan finds nothing,
                    return nothing
            else update bridge dict
        else update bridge dict

    for items
        if validate fails
            create new user

    return updated bridge dict (figuratively)

Enter discovery with ID
    if running upnp finds nothing,
        if running n-upnp finds nothing,
            bail
    if ID provided
        return addr of matching ID
    else
        return any addr

"""
import logging
import urllib.request
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET
import json
from collections import namedtuple

if __name__ is not '__main__':
    from discoverhue.ssdp import discover as ssdp_discover

class DiscoveryError(Exception):
    """ Raised when a discovery method yields no results """
    pass

Bridge = namedtuple('Bridge', ['ip', 'icon', 'user'])
Bridge.__new__.__defaults__ = (None, ) * len(Bridge._fields)
""" Bridge named tuple for storing info

    ip    - base address string as found in URLBase of description file
            assuming form scheme://netloc
    icon  - first found icon file
    user  - whitelist ID as provided by user
"""
    # """TODO: default values on instantiation - change to class?"""

def from_url(location):
    """ HTTP request for page at location returned as string

    malformed url returns ValueError
    nonexistant IP returns URLError
    wrong subnet IP return URLError
    reachable IP, no HTTP server returns URLError
    reachable IP, HTTP, wrong page returns HTTPError
    """
    req = urllib.request.Request(location)
    with urllib.request.urlopen(req) as response:
        the_page = response.read().decode()
        return the_page

def parse_description_xml(location):
    """ Extract serial number, base ip, and img url from description.xml

    missing data from XML returns AttributeError
    malformed XML returns ParseError

    Refer to included example for URLBase and serialNumber elements
    """
    # """TODO: review error handling on xml"""
    # may want to suppress ParseError in the event that it was caused
    # by a none bridge device although this seems unlikely
    try:
        xml_str = from_url(location)
    except urllib.request.HTTPError as error:
        logging.info("No description for %s: %s", location, error)
        return None, error
    except urllib.request.URLError as error:
        logging.info("No HTTP server for %s: %s", location, error)
        return None, error
    else:
        root = ET.fromstring(xml_str)
        rootname = {'root': root.tag[root.tag.find('{')+1:root.tag.find('}')]}
        baseip = root.find('root:URLBase', rootname).text
        device = root.find('root:device', rootname)
        serial = device.find('root:serialNumber', rootname).text
        anicon = device.find('root:iconList', rootname).find('root:icon', rootname)
        imgurl = anicon.find('root:url', rootname).text
        # Alternatively, could look directly in the modelDescription field
        if all(x in xml_str.lower() for x in ['philips', 'hue']):
            return serial, Bridge(ip=baseip, icon=imgurl, user=None)
        else:
            return None, None

def _build_from(baseip):
    """ Build URL for description.xml from ip """
    # """TODO: don't really need the try/except"""
    from ipaddress import ip_address
    try:
        ip_address(baseip)
    except ValueError:
        # """attempt to construct url but the ip format has changed"""
        # logging.warning("Format of internalipaddress changed: %s", baseip)
        if 'http' not in baseip[0:4].lower():
            baseip = urlunsplit(['http', baseip, '', '', ''])
        spl = urlsplit(baseip)
        if '.xml' not in spl.path:
            sep = '' if spl.path.endswith('/') else '/'
            spl = spl._replace(path=spl.path+sep+'description.xml')
        return spl.geturl()
    else:
        # construct url knowing baseip is a pure ip
        return  urlunsplit(('http', baseip, '/description.xml', '', ''))
    # alternatively:
    # baseip = baseip if baseip[0:4].lower() == 'http' else 'http://'+baseip
    # baseip = baseip if baseip[-4:].lower() == '.xml' else baseip+'/description.xml'
    # return baseip

def parse_portal_json():
    """ Extract id, ip from https://www.meethue.com/api/nupnp

    Note: the ip is only the base and needs xml file appended, and
    the id is not exactly the same as the serial number in the xml
    """
    try:
        json_str = from_url('https://www.meethue.com/api/nupnp')
    except urllib.request.HTTPError as error:
        logging.error("Problem at portal: %s", error)
        raise
    except urllib.request.URLError as error:
        logging.warning("Problem reaching portal: %s", error)
        return []
    else:
        portal_list = []
        json_list = json.loads(json_str)
        for bridge in json_list:
            serial = bridge['id']
            baseip = bridge['internalipaddress']
            # baseip should look like "192.168.0.1"
            xmlurl = _build_from(baseip)
            # xmlurl should look like "http://192.168.0.1/description.xml"
            portal_list.append((serial, xmlurl))
        return portal_list

def via_upnp():
    """ Use SSDP as described by the Philips guide """
    ssdp_list = ssdp_discover("ssdp:all", timeout=5)
    #import pickle
    #with open("ssdp.pickle", "wb") as f:
        #pickle.dump(ssdp_list,f)
    bridges_from_ssdp = [u for u in ssdp_list if 'IpBridge' in u.server]
    logging.info('SSDP returned %d items with %d Hue bridges(s).',
                 len(ssdp_list), len(bridges_from_ssdp))
    # Confirm SSDP gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1:80/description.xml
    found_bridges = {}
    for bridge in bridges_from_ssdp:
        serial, bridge_info = parse_description_xml(bridge.location)
        if serial:
            found_bridges[serial] = bridge_info

    logging.debug('%s', found_bridges)
    if found_bridges:
        return found_bridges
    else:
        raise DiscoveryError('SSDP returned nothing')

def via_nupnp():
    """ Use method 2 as described by the Philips guide """
    bridges_from_portal = parse_portal_json()
    logging.info('Portal returned %d Hue bridges(s).',
                 len(bridges_from_portal))
    # Confirm Portal gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1/description.xml
    found_bridges = {}
    for bridge in bridges_from_portal:
        serial, bridge_info = parse_description_xml(bridge[1])
        if serial:
            found_bridges[serial] = bridge_info

    logging.debug('%s', found_bridges)
    if found_bridges:
        return found_bridges
    else:
        raise DiscoveryError('Portal returned nothing')

def via_scan():
    """ IP scan - not implemented """
    raise DiscoveryError()

def valid_whitelist(bridge_tuple):
    return True

def create_new_whitelist(bridge_tuple, appname):
    pass

def find_bridges(prior_bridges=None, create_new_as=None):
    """ Locate Philips Hue bridges

    TODO: more verbosity here
    TODO: add mode to call with IP and return serial?
    TODO: support a list of SN's as input, or something simpler than dict of bridge()
    """
    known_bridges = {}
    found_bridges = {}

    # with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    #     futures = {prior_sn: executor.submit(parse_description_xml, prior_bridge.ip)
    #         for prior_sn, prior_bridge in prior_bridges.items()}

    # Validate caller's provided list
    try:
        prior_bridges_list = list(prior_bridges.items())
    except AttributeError:
        # if caller didnt provide dict then assume single SN or None
        # in either case, the discovery must be executed
        pass
    else:
        for prior_sn, prior_bridge in prior_bridges_list:
            if prior_sn is None:
                continue
            serial, bridge = parse_description_xml(_build_from(prior_bridge.ip))
            if serial == prior_sn:
                # add to known with provided user
                known_bridges[serial] = bridge._replace(user=prior_bridge.user)
                del prior_bridges[serial]
            elif serial:
                # stumbled on another bridge, add to found
                found_bridges[serial] = bridge
            else:
                # nothing usable at that ip
                logging.info('%s not found at %s', prior_sn, prior_bridge.ip)

    # prior_bridges is None, single SN, dict of unfound SNs, or empty dict
    if prior_bridges or prior_bridges is None:
        # do the discovery, was not an empty dict
        try:
            found_bridges.update(via_upnp())
        except DiscoveryError:
            try:
                found_bridges.update(via_nupnp())
            except DiscoveryError:
                try:
                    found_bridges.update(via_scan())
                except DiscoveryError:
                    logging.warning("All discovery methods returned nothing")

        if prior_bridges:
            # prior_bridges is either single SN or dict of unfound SNs
            # first assume single Serial SN string
            try:
                ip_address = found_bridges[prior_bridges].ip
            except TypeError:
                # user passed an invalid type for key
                # presumably it's a dict meant for alternate mode
                logging.debug('Assuming alternate mode, prior_bridges is type %s.',
                              type(prior_bridges))
            except KeyError:
                # user provided Serial Number was not found
                return None
            else:
                # note there's no whitelist name provided in this mode
                # so there's no need to validate/create
                return ip_address
            # assume user passed a dict of Serial IDs with whitelist info
            for serial in list(found_bridges.keys()):
                try:
                    # update found bridge with whitelisted user from caller
                    prior_user = prior_bridges[serial].user
                    combined = found_bridges[serial]._replace(user=prior_user)
                    known_bridges[serial] = combined
                except TypeError:
                    # presumably still dealing with user input that wasn't a dict
                    break
                except KeyError:
                    # requested serial number wasn't found in discovery
                    continue
                else:
                    del prior_bridges[serial]
                    del found_bridges[serial]
        else:
            # prior_bridges is None, move on to whitelist checks
            pass
    else:
        # skip discovery, prior_bridges dict was emptied already
        pass

    # prior_bridges is None, dict of unfound SNs, or empty dict
    # found_bridges is dict of found SNs or empty
    # known_bridges is dict of found SNs with user

    # """TODO: Any value in checking the whitelist validity even if not creating?""""
    if create_new_as:
        for serial in known_bridges:
            if valid_whitelist(known_bridges[serial]):
                create_new_whitelist(known_bridges[serial], create_new_as)

    # is anything left in prior_bridges?
    if prior_bridges is not None:
        for serial in prior_bridges:
            logging.warning('Could not locate bridge with Serial ID %s', serial)
            # """TODO: decide how to handle unresolved bridges""""

    found_bridges.update(known_bridges)
    return found_bridges


def check_bridges():
    """ Check IP and white list access, no scan """
    pass

if __name__ == '__main__':
    from ssdp import discover as ssdp_discover
    logging.basicConfig(level=logging.DEBUG,                                                 \
        format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s', \
        datefmt="%Y-%m-%d %H:%M:%S")
    # known = {'0017884e7dad': Bridge(ip='someip', icon='someurl', user='someuser')}
    # malformed = {'0017884e7dad': 'gibberish'} # results in AttributeError
    KNOWN = {'0017884e7dad': Bridge('http://192.168.0.16:80/', None, None)}
    print(find_bridges(KNOWN))
