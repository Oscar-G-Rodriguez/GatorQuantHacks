"""Offline checks of rate handling and immutable acquisition resume."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from discovery.io import ROOT, digest, identity, write_json
from discovery.options_data import Cache

spec = importlib.util.spec_from_file_location("transport_fixture", ROOT/"tools/check_massive_coverage.py")
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class Clock:
    def __init__(self):
        self.t, self.waits = 0, []

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.t += seconds


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return b'{"status":"OK","results":[]}'


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()
        self.addCleanup(patch.stopall)
        patch.object(coverage, "time", self.clock).start()
        self.opener = patch.object(coverage, "build_opener").start().return_value
        self.opener.open.return_value = Response()

    def client(self, cap=20, fast=True):
        return coverage.Client("fixture-key", Path(self.tmp.name), cap,
                               **({"minimum_interval":.5,"separate_buckets":True} if fast else {}))

    def test_default_preserves_shared_conservative_pace(self):
        client = self.client(fast=False)
        client.get("stock", "/v2/aggs/ticker/AAPL/range/1/day/2024-01-02/2024-01-02")
        client.get("option", "/v3/quotes/O%3AFIXTURE")
        self.assertEqual(self.clock.t, 12.5)
        self.assertEqual(client.receipts[-1]["pacing_bucket"], "shared")

    def test_fast_buckets_have_independent_clocks(self):
        client = self.client()
        client.get("option", "/v3/quotes/O%3AFIXTURE")
        client.get("reference", "/v3/reference/options/contracts")
        client.get("option", "/v2/aggs/ticker/O%3AFIXTURE/range/1/day/2024-01-02/2024-01-02")
        self.assertEqual(self.clock.t, .5)
        self.assertEqual([r["pacing_bucket"] for r in client.receipts], ["options","reference","options"])

    def test_429_retries_count_and_only_slow_affected_bucket(self):
        error = HTTPError("https://api.massive.com/v3/quotes/O%3AFIXTURE",429,"limited",{"Retry-After":"90"},None)
        self.opener.open.side_effect = [error, Response(), Response()]
        client = self.client()
        client.get("option", "/v3/quotes/O%3AFIXTURE")
        client.get("reference", "/v3/reference/options/contracts")
        self.assertEqual([r["http_status"] for r in client.receipts], [429,200,200])
        self.assertEqual(client.bucket_intervals, {"options":12.5})
        self.assertEqual(client.receipts[-1]["minimum_interval_seconds"], .5)
        self.assertEqual(self.clock.t, 90)
        self.assertTrue(all(w <= 60 for w in self.clock.waits))

    def test_retry_cap_and_authorization_failure_are_bounded(self):
        for code in [429,403]:
            with self.subTest(code=code):
                self.opener.open.side_effect = HTTPError("https://api.massive.com/",code,"failure",{},None)
                client = self.client(cap=1)
                with self.assertRaises(coverage.AccessFailure):
                    client.get("option", "/v3/quotes/O%3AFIXTURE")
                self.assertEqual(len(client.receipts),1)
        self.assertEqual(self.clock.t,0)

    def test_malformed_retry_delay_remains_finite(self):
        for value in [None,"invalid","NaN","inf","-1"]:
            self.assertEqual(coverage.Client.retry_delay(value),60)

    def test_completed_object_reuses_bytes_even_without_request_budget(self):
        folder = Path(self.tmp.name)
        request = {"path":"/v3/quotes/O%3AFIXTURE","params":{"limit":1},"paginate":False}
        oid = identity(request)
        obj = folder/f"{oid}.json"
        write_json(obj,[{"sip_timestamp":1}])
        write_json(folder/f"{oid}.receipt.json",{"spec":request,"sha256":digest(obj),"rows":1})
        write_json(folder/"attempt-prior.json",{"requests":[{"http_status":200}]})
        with patch("discovery.options_data.os.getenv",return_value="fixture-key"):
            cache = Cache(folder,cap=1,minimum_interval=.5)
            self.assertEqual(cache.pages("cached",request["path"],request["params"],False),[{"sip_timestamp":1}])
        self.assertEqual(cache.client.receipts,[])
        self.assertEqual(cache.prior_count,1)


if __name__ == "__main__":
    unittest.main()
