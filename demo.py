""" Demo file of use """
import discoverhue

# Call with no parameter to discover all bridges
# Returns a dictionary of found `serial number: ip address` pairs
print("Searching for any bridges...")
found = discoverhue.find_bridges()
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge]))

# Call with a dictionary of `serial number: ip address` pairs
# Will check the provided ip for a bridge matching serial number
# Will attempt discovery if not all bridges were matched
# Returns a dictionary of found `serial number: ip address` pairs
search_id = {'0017884e7dad':'192.168.0.1',
             '001788102201':'192.168.0.2'}
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.find_bridges(search_id)
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge]))

# Call with a string representing serial number
# Will discover and return a string of the base ip address
search_id = '0017884e7dad'
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.find_bridges(search_id)
print(found)
