import json, re, sys
data = open(sys.argv[1], "rb").read()
A = (233138901, data.find(b"]", 233139376)); B = (237424660, data.find(b"]", 237424854))
def items(a): return re.findall(r'"([a-z_]+)"', data[a[0]:a[1]].decode("latin-1"))
sa, sb = items(A), items(B)
win = (220055868 - 300000, 220055868 + 300000)
seg = data[win[0]:win[1]].decode("latin-1")
rm = {}
for m in re.finditer(r'[{,]([a-z_]+):\((?:e|e,n|e,n,r|)\)=>', seg):
    rm.setdefault(m.group(1), win[0] + m.start(1))
out = {}
for t in sorted(set(sa) | set(sb) | set(rm)):
    q = ('"%s"' % t).encode()
    out[t] = {"set_O": data.find(q, A[0], A[1]) if t in sa else None, "list_bv": data.find(q, B[0], B[1]) if t in sb else None,
              "render": rm.get(t), "creates": len(re.findall(rb'type:"' + t.encode() + rb'"', data)),
              "type_eq": len(re.findall(rb'type==="' + t.encode() + rb'"', data))}
print(json.dumps(out))
