""" Demo file of use """
import discoverhue

print("Searching for any bridges...")
found = discoverhue.get_hue_bridges()
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge].ip))

search_id = '0017884e7dad'
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.get_hue_bridges(search_id)
print(found)

search_id = 'deadbeef'
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.get_hue_bridges(search_id)
print(found)

search_id = {'0017884e7dad':discoverhue.Bridge(None, None, None),
             'deadbeef':discoverhue.Bridge(None, None, None)}
print("\nSearching for {s}...".format(s=search_id))
found = discoverhue.get_hue_bridges(search_id)
print("Found {}".format(len(found)))
for bridge in found:
    print('    Bridge ID {br} at {ip}'.format(br=bridge, ip=found[bridge].ip))
