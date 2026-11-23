import hashlib, json, re, sys
data = open(sys.argv[1], "rb").read()
out = {"binary_sha256": hashlib.sha256(data).hexdigest(), "arrays": [], "render_map": None}
def array_at(off):
    s = data.rfind(b"[", 0, off); e = data.find(b"]", off)
    body = data[s + 1:e].decode("latin-1")
    items = re.findall(r'"([a-z_]+)"', body)
    return s, e, items, body.count(",") + 1
for off in (233139376, 237424854):
    s, e, items, n = array_at(off)
    pre = data[max(0, s - 60):s].decode("latin-1")
    out["arrays"].append({"near": off, "start": s, "end": e, "n_items": len(items), "n_commas": n,
                          "prefix": "".join(c if 32 <= ord(c) < 127 else "." for c in pre), "items": items,
                          "sha256": hashlib.sha256(data[s:e + 1]).hexdigest()})
# the render map: object of `key:(e)=>` entries around 220055868
i = 220055868
lo = data.rfind(b"={", i - 400000, i)
seg = data[i - 300000:i + 300000].decode("latin-1")
keys = re.findall(r'[{,]([a-z_]+):\(e\)=>', seg)
out["render_map"] = {"near": i, "keys_in_window": sorted(set(keys)), "n": len(set(keys))}
print(json.dumps(out, indent=1))
