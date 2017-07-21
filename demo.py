""" Demo file of use """
import discoverhue

print("Searching for any bridges...")
found = discoverhue.find_bridges()
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge].ip))

search_id = '0017884e7dad'
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.find_bridges(search_id)
print(found)

search_id = 'deadbeef'
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.find_bridges(search_id)
print(found)

search_id = {'0017884e7dad':discoverhue.Bridge('192.168.0.1'),
             'deadbeef':discoverhue.Bridge('192.168.0.2')}
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.find_bridges(search_id)
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge].ip))
