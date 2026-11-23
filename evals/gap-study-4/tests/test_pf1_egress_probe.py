#!/usr/bin/env python3
"""Lane pf1-l3-transcript-integrity (Gap Study round 4; fold plan prefreeze-1, the lane orchestrator's approval of
Sat 24 Oct 2026 under Javier's standing delegation): pre-freeze review 1's m9, the preflight's direct-egress probe.

  E1-program    box/preflight.DIRECT_PROGRAM run in this process on fake route tables (a default route; an internal
                network with no default route) and a fake connect: the gateway candidates are the route table's gateways
                and the first host of each on-link network, every GATEWAY_PORTS port is tried on each, every target is
                tried at its address, and a connection made is recorded as one; it opens /proc/net/route alone.
  E2-checks     the program's own output judged by the three checks: clean when nothing connected, red when the gateway,
                a raw IP or the metadata address connected, and red when the inspect's gateway was not tried.
  E3-bound      the probe's argv carries the timeout, the ports and the targets from the module's constants, and the
                draft's named residual names the same addresses and ports.

Witnesses: a program that skips the on-link first host, and a gateway check that never reads the inspect, are each
caught. No process, network or credential: the connect is a fake, the route table a string.
"""

from __future__ import annotations

import builtins
import contextlib
import copy
import io
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_draft  # noqa: E402
from box import preflight as pf  # noqa: E402

HEADER = "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
# 172.30.0.1 as /proc/net/route spells it (little-endian hex): 01 00 1E AC; the /16 network 00 00 1E AC, mask FF FF 00 00
DEFAULT_ROUTE = HEADER + ("eth0\t00000000\t01001EAC\t0003\t0\t0\t0\t00000000\t0\t0\t0\n"
                          "eth0\t00001EAC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n")
INTERNAL_ONLY = HEADER + "eth0\t00001FAC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n"   # 172.31.0.0/16, no gateway


class FakeSocket:
    def close(self):
        pass


def run_program(table: str, *, connects=(), program=None) -> tuple:
    """(the program's JSON output, the (address, port) pairs it tried, the paths it opened)."""
    tried, opened = [], []
    real_open = builtins.open

    def fake_open(path, *a, **k):
        opened.append(str(path))
        if path == "/proc/net/route":
            return io.StringIO(table)
        return real_open(path, *a, **k)

    def fake_connect(addr, timeout=None):
        tried.append(tuple(addr))
        if tuple(addr) in connects:
            return FakeSocket()
        raise TimeoutError("timed out")

    argv = ["-c", str(pf.DIRECT_TIMEOUT_S), ",".join(map(str, pf.GATEWAY_PORTS)), *pf.direct_target_args()]
    buf = io.StringIO()
    with mock.patch.object(builtins, "open", fake_open), mock.patch.object(socket, "create_connection", fake_connect), \
            mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(buf):
        exec(compile(program or pf.DIRECT_PROGRAM, "<direct-egress>", "exec"), {"__name__": "__main__"})
    return json.loads(buf.getvalue()), tried, opened


# Lane pf1-gateway: the take's spec (its network id binds the host-side network record) and that record. By default
# the record names no gateway (IPAM.Config empty), so every case above it judges on the take inspect's Gateway alone.
SPEC = pf.run_take.TakeSpec(image="sha256:" + "a" * 64, run_tree="/srv/w0/t1/tree", config_dir="/srv/w0/t1/cfg",
                            network="b" * 64, memory_reservation=512, memory=1536, cpus="1", pids_limit=64)
NO_HOST_GATEWAY = [{"Name": "n", "Id": "b" * 64, "Internal": True, "IPAM": {"Driver": "default", "Options": {},
                                                                            "Config": []}}]


def raw_for(out: dict, gateway: str | None, *, host=NO_HOST_GATEWAY) -> dict:
    nets = {"n": {"Gateway": gateway or ""}}
    raw = {"direct-egress": {"returncode": 0, "stdout": json.dumps(out), "stderr": ""},
           "take-inspect": {"returncode": 0, "stdout": json.dumps([{"NetworkSettings": {"Networks": nets}}]),
                            "stderr": ""}}
    if host is not None:
        raw["take-network-inspect"] = {"returncode": 0, "stdout": json.dumps(host), "stderr": ""}
    return raw


def judged(raw: dict) -> dict:
    out = {}
    for cid, fn in (("egress-raw-ip-refused", pf._check_raw_ip), ("egress-metadata-refused", pf._check_metadata),
                    ("egress-gateway-refused", pf._check_gateway)):
        try:
            out[cid] = (True, fn(raw, SPEC))
        except pf._Fail as e:
            out[cid] = (False, str(e))
    return out


class E1Program(unittest.TestCase):
    def test_default_route_table(self):
        out, tried, opened = run_program(DEFAULT_ROUTE)
        self.assertEqual(out["gateway_candidates"], ["172.30.0.1"])     # the gateway, and the /16's first host
        self.assertEqual(sorted(out["gateway"]["172.30.0.1"]), sorted(map(str, pf.GATEWAY_PORTS)))
        self.assertEqual(sorted(out["targets"]), sorted(pf.DIRECT_TARGETS))
        want = {("172.30.0.1", p) for p in pf.GATEWAY_PORTS} | set(pf.DIRECT_TARGETS.values())
        self.assertEqual(set(tried), want)
        self.assertEqual(opened, ["/proc/net/route"])
        self.assertFalse(any(r["connected"] for r in out["targets"].values()))
        self.assertEqual({r["error"] for r in out["gateway"]["172.30.0.1"].values()}, {"TimeoutError"})

    def test_internal_network_with_no_default_route(self):
        out, tried, _ = run_program(INTERNAL_ONLY)
        self.assertEqual(out["gateway_candidates"], ["172.31.0.1"])
        self.assertEqual(len([t for t in tried if t[0] == "172.31.0.1"]), len(pf.GATEWAY_PORTS))

    def test_a_connection_is_recorded(self):
        out, _, _ = run_program(DEFAULT_ROUTE, connects={("172.30.0.1", 22), ("169.254.169.254", 80)})
        self.assertIs(out["gateway"]["172.30.0.1"]["22"]["connected"], True)
        self.assertIs(out["targets"]["metadata"]["connected"], True)
        self.assertIs(out["targets"]["raw-ip-a"]["connected"], False)


class E2Checks(unittest.TestCase):
    def test_clean(self):
        out, _, _ = run_program(DEFAULT_ROUTE)
        got = judged(raw_for(out, "172.30.0.1"))
        self.assertEqual({k: v[0] for k, v in got.items()}, dict.fromkeys(got, True), got)

    def test_an_empty_inspect_gateway_refuses(self):
        """The lane orchestrator's ruling on review fb354328 finding 5: an empty Gateway (as an --internal network may
        report) fails closed, whatever the route table's first host is; the candidates are never bound on their own."""
        out, _, _ = run_program(INTERNAL_ONLY)
        ok, detail = judged(raw_for(out, None))["egress-gateway-refused"]
        self.assertFalse(ok)
        self.assertIn("names no gateway", detail)
        ok, _ = judged(raw_for(out, "172.31.0.1"))["egress-gateway-refused"]
        self.assertTrue(ok)

    def test_each_connection_is_red(self):
        for target, cid in ((("172.30.0.1", 2375), "egress-gateway-refused"), (("1.1.1.1", 443), "egress-raw-ip-refused"),
                            (("8.8.8.8", 443), "egress-raw-ip-refused"),
                            (("169.254.169.254", 80), "egress-metadata-refused")):
            out, _, _ = run_program(DEFAULT_ROUTE, connects={target})
            got = judged(raw_for(out, "172.30.0.1"))
            self.assertFalse(got[cid][0], (target, got))
            self.assertEqual([k for k, v in got.items() if not v[0]], [cid], target)

    def test_the_inspects_gateway_must_be_tried(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        self.assertFalse(judged(raw_for(out, "172.30.0.1"))["egress-gateway-refused"][0])

    def test_an_answered_refusal_is_named_not_failed(self):
        out, _, _ = run_program(DEFAULT_ROUTE)
        out["gateway"]["172.30.0.1"]["22"]["error"] = "ConnectionRefusedError"
        ok, detail = judged(raw_for(out, "172.30.0.1"))["egress-gateway-refused"]
        self.assertTrue(ok)
        self.assertIn("172.30.0.1:22", detail)

    def test_witness_a_program_without_the_on_link_host_is_caught(self):
        skip = pf.DIRECT_PROGRAM.replace("cands.add(socket.inet_ntoa((net + 1).to_bytes(4, \"big\")))", "pass")
        self.assertNotEqual(skip, pf.DIRECT_PROGRAM, "witness not performed")
        out, _, _ = run_program(INTERNAL_ONLY, program=skip)
        self.assertFalse(judged(raw_for(out, None))["egress-gateway-refused"][0])

    def test_witness_a_check_blind_to_the_inspect_is_caught(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        with mock.patch.object(pf, "_inspect_gateways", lambda obj, host=None: []):
            self.assertTrue(judged(raw_for(out, "172.30.0.1"))["egress-gateway-refused"][0], "witness not performed")
        self.assertFalse(judged(raw_for(out, "172.30.0.1"))["egress-gateway-refused"][0])


# Lane pf1-gateway (glitch-45's ruling, Mon 26 Oct 2026, under Javier's standing delegation): the first arm O re-walk
# at the freeze line, w-o48, failed its preflight before turn 1 on egress-gateway-refused. Its records are committed on
# branch walk/w-kptgozIX (commit e81b6f2f) in the walk-records repo: rehearsals/w-o48/launch.json (blob f76b847c) and
# preflight.json (blob 13674507). Copied from them, never edited:
W_O48_NETWORK_ID = "1eba86a76442fcfae3cbfcf00d2842c9dbbfb0b674544a04cf49a96f38832dc1"   # launch.json network_id
W_O48_NETWORKS = {"nc381ca9735e8e95c6361eedd": {   # launch.json, step take-inspect: inspect.NetworkSettings.Networks
    "Aliases": None, "DNSNames": None, "DriverOpts": None, "EndpointID": "", "Gateway": "", "GlobalIPv6Address": "",
    "GlobalIPv6PrefixLen": 0, "GwPriority": 0, "IPAMConfig": None, "IPAddress": "", "IPPrefixLen": 0,
    "IPv6Gateway": "", "Links": None, "MacAddress": "", "NetworkID": ""}}
W_O48_DETAIL = ("the take inspect names no gateway for network(s) ['nc381ca9735e8e95c6361eedd']: the addresses tried "
                "cannot be bound to the take's own gateway (fail closed)")   # preflight.json, egress-gateway-refused
# Not in w-o48's records (preflight.json keeps no probe output, and the network was removed at teardown), so taken from
# athena's Docker 29.8.1 live on 26 Oct 2026 for a fresh `docker network create --internal` network: `docker network
# inspect` named IPAM.Config [{"Gateway": "172.18.0.1", "Subnet": "172.18.0.0/16"}], a container on it showed
# NetworkSettings.Networks.<n>.Gateway "" and this one-line /proc/net/route (an on-link /16, no default route).
ATHENA_INTERNAL_ROUTE = HEADER + "eth0\t000012AC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n"   # 172.18.0.0/16
W_O48_SPEC = pf.run_take.TakeSpec(image="sha256:" + "a" * 64, run_tree="/srv/w0/t1/tree", config_dir="/srv/w0/t1/cfg",
                                  network=W_O48_NETWORK_ID, memory_reservation=512, memory=1536, cpus="1",
                                  pids_limit=64)


def network_record(gateways=(), *, name="n", net_id=None) -> list:
    """`docker network inspect <id>`'s output for the take's network: the host-side record, outside the take's reach."""
    return [{"Name": name, "Id": SPEC.network if net_id is None else net_id, "Internal": True,
             "IPAM": {"Driver": "default", "Options": {},
                      "Config": [{"Subnet": g.rsplit(".", 1)[0] + ".0/16", "Gateway": g} for g in gateways]}}]


def raw_w_o48(out: dict, host: list | None) -> dict:
    raw = {"direct-egress": {"returncode": 0, "stdout": json.dumps(out), "stderr": ""},
           "take-inspect": {"returncode": 0, "stderr": "",
                            "stdout": json.dumps([{"NetworkSettings": {"Networks": copy.deepcopy(W_O48_NETWORKS)}}])}}
    if host is not None:
        raw["take-network-inspect"] = {"returncode": 0, "stdout": json.dumps(host), "stderr": ""}
    return raw


def gateway_judged(raw: dict, spec=None) -> tuple:
    try:
        return True, pf._check_gateway(raw, SPEC if spec is None else spec)
    except pf._Fail as e:
        return False, str(e)


class E4HostRecord(unittest.TestCase):
    """The expected gateway bound to a host-side record of the take's network (`docker network inspect`'s IPAM
    gateway) when the take inspect names none, as Docker reports for an --internal network; never the route table's
    word alone, and fail closed when neither names one."""

    def test_w_o48_recorded_input_passes_with_the_host_record(self):
        """Red at the freeze line (7a866455): the recorded detail, word for word. Green once the host record binds."""
        out, _, _ = run_program(ATHENA_INTERNAL_ROUTE)
        self.assertEqual(out["gateway_candidates"], ["172.18.0.1"])
        host = network_record(["172.18.0.1"], name="nc381ca9735e8e95c6361eedd", net_id=W_O48_NETWORK_ID)
        ok, detail = gateway_judged(raw_w_o48(out, host), W_O48_SPEC)
        self.assertNotEqual(detail, W_O48_DETAIL, "the w-o48 refusal reproduced")
        self.assertTrue(ok, detail)
        self.assertIn("172.18.0.1", detail)

    def test_w_o48_without_a_gateway_in_the_host_record_still_refuses(self):
        out, _, _ = run_program(ATHENA_INTERNAL_ROUTE)
        host = network_record([], name="nc381ca9735e8e95c6361eedd", net_id=W_O48_NETWORK_ID)
        ok, detail = gateway_judged(raw_w_o48(out, host), W_O48_SPEC)
        self.assertFalse(ok)
        self.assertTrue(detail.startswith(W_O48_DETAIL[:-len(" (fail closed)")]), detail)
        self.assertIn("fail closed", detail)

    def test_internal_network_passes_with_the_host_record(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        ok, detail = gateway_judged(raw_for(out, None, host=network_record(["172.31.0.1"])))
        self.assertTrue(ok, detail)

    def test_the_host_gateway_must_be_among_the_addresses_tried(self):
        out, _, _ = run_program(INTERNAL_ONLY)              # tries 172.31.0.1 only
        ok, detail = gateway_judged(raw_for(out, None, host=network_record(["172.30.0.1"])))
        self.assertFalse(ok)
        self.assertIn("172.30.0.1", detail)
        self.assertIn("was not among the addresses tried", detail)

    def test_a_connection_to_the_host_gateway_is_red(self):
        for port in pf.GATEWAY_PORTS:
            out, _, _ = run_program(INTERNAL_ONLY, connects={("172.31.0.1", port)})
            ok, detail = gateway_judged(raw_for(out, None, host=network_record(["172.31.0.1"])))
            self.assertFalse(ok, port)
            self.assertIn("a direct connection to gateway 172.31.0.1", detail)

    def test_no_host_record_and_no_container_gateway_refuses(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        for why, host in (("names nothing", network_record([])), ("missing", None)):
            ok, detail = gateway_judged(raw_for(out, None, host=host))
            self.assertFalse(ok, why)
        ok, detail = gateway_judged(raw_for(out, None, host=network_record([])))
        self.assertIn("names no gateway", detail)
        self.assertIn("fail closed", detail)

    def test_a_record_of_another_network_binds_nothing(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        for why, host in (("another id", network_record(["172.31.0.1"], net_id="9" * 64)),
                          ("another name", network_record(["172.31.0.1"], name="other")),
                          ("two networks", network_record(["172.31.0.1"]) * 2),
                          ("not a list", {"IPAM": {"Config": [{"Gateway": "172.31.0.1"}]}}),
                          ("off shape", [{"Name": "n", "Id": SPEC.network, "IPAM": {"Config": "172.31.0.1"}}])):
            ok, detail = gateway_judged(raw_for(out, None, host=host))
            self.assertFalse(ok, (why, detail))

    def test_a_container_network_id_that_differs_binds_nothing(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        raw = raw_for(out, None, host=network_record(["172.31.0.1"]))
        doc = json.loads(raw["take-inspect"]["stdout"])
        doc[0]["NetworkSettings"]["Networks"]["n"]["NetworkID"] = "9" * 64
        raw["take-inspect"]["stdout"] = json.dumps(doc)
        self.assertFalse(gateway_judged(raw)[0])

    def test_a_non_internal_network_keeps_passing_as_before(self):
        """The container inspect names its Gateway: passes whether the host record repeats it or names nothing."""
        out, _, _ = run_program(DEFAULT_ROUTE)
        for host in (network_record(["172.30.0.1"]), network_record([])):
            ok, detail = gateway_judged(raw_for(out, "172.30.0.1", host=host))
            self.assertTrue(ok, detail)
            self.assertEqual(detail, gateway_judged(raw_for(out, "172.30.0.1"))[1])

    def test_witness_a_check_that_ignores_the_host_record_is_caught(self):
        out, _, _ = run_program(INTERNAL_ONLY)
        raw = raw_for(out, None, host=network_record(["172.31.0.1"]))
        self.assertTrue(gateway_judged(raw)[0])
        with mock.patch.object(pf, "_host_network_gateways", lambda raw, spec: {}):
            self.assertFalse(gateway_judged(raw)[0], "witness not performed")


class E3Bound(unittest.TestCase):
    def test_the_probe_argv(self):
        spec = pf.run_take.TakeSpec(image="sha256:" + "a" * 64, run_tree="/srv/w0/t1/tree", config_dir="/srv/w0/t1/cfg",
                                    network="b" * 64, memory_reservation=512, memory=1536, cpus="1", pids_limit=64)
        hosts = {h: f"{h}.example" for h in pf.run_take.LOGIN_VARIABLE}
        probes = pf.probes(spec, take_id="c" * 64, sidecar_id="d" * 64, harness=pf.run_take.CLAUDE_CODE, hosts=hosts,
                           evidence_dir="/srv/w0/rec/ev", sidecar_image="sha256:" + "e" * 64, proxy_id="f" * 64,
                           proxy_image="sha256:" + "1" * 64)
        argv = [p for p in probes if p.id == "direct-egress"][0].argv
        tail = list(argv[list(argv).index("-c") + 1:])
        self.assertEqual(tail, [pf.DIRECT_PROGRAM, str(pf.DIRECT_TIMEOUT_S), ",".join(map(str, pf.GATEWAY_PORTS)),
                                *pf.direct_target_args()])
        self.assertEqual(pf.PROBE_IDS[-1], "direct-egress")
        self.assertEqual(pf.PREFLIGHT_CHECKS[-3:], ("egress-raw-ip-refused", "egress-metadata-refused",
                                                    "egress-gateway-refused"))

    def test_the_residual_names_the_constants(self):
        text = build_draft.PF1_READS_EGRESS_RESIDUAL["text"]
        ports = ", ".join(map(str, pf.GATEWAY_PORTS[:-1])) + " and " + str(pf.GATEWAY_PORTS[-1])
        self.assertIn(f"on ports {ports} (egress-gateway-refused)", text)
        for label in pf.RAW_IP_TARGETS:
            self.assertIn(pf.DIRECT_TARGETS[label][0], text)
        self.assertIn(f"{pf.DIRECT_TARGETS[pf.METADATA_TARGET][0]} on port {pf.DIRECT_TARGETS[pf.METADATA_TARGET][1]}",
                      text)
        for cid in ("egress-raw-ip-refused", "egress-metadata-refused", "egress-gateway-refused"):
            self.assertIn(cid, text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
