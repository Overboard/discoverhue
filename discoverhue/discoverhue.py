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
    if running upnp finds nothing,
        if runninf n-upnp finds nothing
            done?
        else
            update bridge dict
    else
        update bridge dict

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
import xml.etree.ElementTree as ET
import json
from collections import namedtuple

if __name__ is not '__main__':
    from discoverhue.ssdp import discover as ssdp_discover

Bridge = namedtuple('Bridge', ['ip', 'icon', 'user'])

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

    # TODO: review error handling on xml
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
        return serial, Bridge(ip=baseip, icon=imgurl, user=None)

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
            baseip = bridge['internalipaddress']
            baseip = baseip if baseip[0:4].lower() == 'http' else 'http://'+baseip
            baseip = baseip if baseip[-4:].lower() == '.xml' else baseip+'/description.xml'
            serial = bridge['id']
            portal_list.append((serial, baseip))
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
    return found_bridges

def via_nupnp():
    """ Use method 2 as described by the Philips guide """
    bridges_from_portal = parse_portal_json()
    logging.info('Portal returned %d Hue bridges(s).',
                 len(bridges_from_portal))
    # Confirm Portal gave an accessible bridge device by reading from the returned
    # location.  Should look like: http://192.168.0.1:80/description.xml
    found_bridges = {}
    for bridge in bridges_from_portal:
        serial, bridge_info = parse_description_xml(bridge[1])
        if serial:
            found_bridges[serial] = bridge_info

    logging.debug('%s', found_bridges)
    return found_bridges

def valid_whitelist(bridge_tuple):
    return True

def create_new_whitelist(bridge_tuple, appname):
    pass

def get_hue_bridges(prior_bridges=None, create_new_as=None):
    """ Locate Philips Hue bridges

    TODO: more verbosity here
    """
    found_bridges = {}
    found_bridges.update(via_upnp())
    if not found_bridges:
        found_bridges.update(via_nupnp())

    # returning all found bridges
    if prior_bridges is None:
        return found_bridges

    # assume user passed a single Serial ID string
    try:
        ip_address = found_bridges[prior_bridges].ip
    except TypeError:
        # user passed an invalid type for key
        # presumably it's a dict meant for alternate mode
        logging.debug('Assuming alternate mode, prior_bridges is type %s.',
                      type(prior_bridges))
    except KeyError:
        # user provided Serial ID was not found
        return None
    else:
        # note there's no whitelist name provided in this mode
        # so there's no need to validate/create
        # TODO: fix nomenclature above
        return ip_address
    # assume user passed a dict of Serial IDs with whitelist info
    for serial_id in found_bridges:
        if serial_id in prior_bridges:
            # update found bridge with whitelisted user from caller
            found_bridges[serial_id]._replace(user=prior_bridges[serial_id].user)
            del prior_bridges[serial_id]
            if create_new_as and not valid_whitelist(found_bridges[serial_id]):
                create_new_whitelist(found_bridges[serial_id], create_new_as)
        else:
            if create_new_as:
                create_new_whitelist(found_bridges[serial_id], create_new_as)
    # is anything left in prior_bridges?
    for serial_id in prior_bridges:
        logging.warning('Could not locate bridge with Serial ID %s', serial_id)
        # TODO: decide how to handle unresolved bridges
    return found_bridges
    # TODO: decide what to return 


if __name__ == '__main__':
    from ssdp import discover as ssdp_discover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s',
                        datefmt="%Y-%m-%d %H:%M:%S")
    # known = {'0017884e7dad': Bridge(ip='someip', icon='someurl', user='someuser')}
    # malformed = {'0017884e7dad': 'gibberish'} # results in AttributeError
    print(get_hue_bridges())
