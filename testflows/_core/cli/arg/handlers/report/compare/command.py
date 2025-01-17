# Copyright 2020 Katteli Inc.
# TestFlows.com Open-Source Software Testing Framework (http://testflows.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import os
import sys
import json
import time
import base64
import threading

from datetime import datetime

import testflows.settings as settings
import testflows._core.cli.arg.type as argtype

from testflows._core import __version__
from testflows._core.flags import Flags, SKIP, RETRY
from testflows._core.testtype import TestType
from testflows._core.cli.arg.common import epilog
from testflows._core.cli.arg.common import HelpFormatter
from testflows._core.cli.arg.handlers.report.copyright import copyright
from testflows._core.transform.log.pipeline import ResultsLogPipeline
from testflows._core.utils.sort import human
from testflows._core.utils.timefuncs import localfromtimestamp, strftimedelta
from testflows._core.filters import The
from testflows._core.name import sep
from testflows._core.transform.log.report.totals import Counts
from testflows._core.cli.arg.handlers.handler import Handler as HandlerBase

logo = '<img class="logo" src="data:image/png;base64,%(data)s" alt="logo"/>'
testflows = '<span class="testflows-logo"></span> [<span class="logo-test">Test</span><span class="logo-flows">Flows</span>]'
testflows_em = testflows.replace("[", "").replace("]", "")

template = f"""
<section class="clearfix">%(logo)s%(confidential)s%(copyright)s</section>

---
# %(title)s Comparison Report
%(body)s

---
Generated by {testflows} Open-Source Test Framework

[<span class="logo-test">Test</span><span class="logo-flows">Flows</span>]: https://testflows.com
"""

class Formatter:
    def format_logo(self, data):
        if not data["company"].get("logo"):
            return ""
        data = base64.b64encode(data["company"]["logo"]).decode("utf-8")
        return '\n<p>' + logo % {"data": data} + "</p>\n"

    def format_confidential(self, data):
        if not data["company"].get("confidential"):
            return ""
        return f'\n<p class="confidential">Document status - Confidential</p>\n'

    def format_copyright(self, data):
        if not data["company"].get("name"):
            return ""
        return (f'\n<p class="copyright">\n'
            f'{copyright(data["company"]["name"])}\n'
            "</p>\n")

    def format_metadata(self, data):
        metadata = data["metadata"]
        s = (
            "\n\n"
            f"||**Date**||{localfromtimestamp(metadata['date']):%b %d, %Y %-H:%M}||\n"
            f'||**Framework**||'
            f'{testflows} {metadata["version"]}||\n'
        )
        if metadata.get("order-by"):
            s += f'||**Order By**||{metadata["order-by"].capitalize()}||\n'
        if metadata.get("sort"):
            s += f'||**Sort**||{"Ascending" if metadata["sort"] == "asc" else "Descending"}||\n'
        if metadata.get("filter"):
            s += f'||**Filter**||{metadata["filter"]}||\n'
        return s + "\n"

    def format_reference(self, data):
        table = data["table"]
        s = "\n\n## Reference\n\n"
        # reference table
        s += " | ".join(table["reference"]["header"]) + "\n"
        s += " | ".join(["---"] * len(table["reference"]["header"])) + "\n"
        for row in table["reference"]["rows"]:
            s += " | ".join(row) + "\n"
        return s

    def format_table(self, data):
        table = data["table"]
        s = "\n\n## Comparison\n\n"
        # comparison table
        s += " | ".join(table["header"]) + "\n"
        s += " | ".join(["---"] * len(table["header"])) + "\n"
        span = '<span class="result result-%(cls)s">%(name)s</span>'
        for row in table["rows"]:
            name, *results = row
            s += " | ".join([name] + [
                span % {'cls': result["result_type"].lower() if result else 'na', 'name': result["result_type"] if result else '-'} for result in results
            ]) + "\n"
        return s

    def format_chart(self, data):
        script = """
        window.onload = function() {
            window.chart = c3.generate({
                bindto: '#data-chart',
                legend: {
                    position: 'inset',
                    inset: {
                        anchor: 'top-right',
                        x: 50,
                        y: -30,
                        step: 1
                    }
                },
                padding: {
                    top: 30
                },
                data: {
                    x: 'x',
                    columns: [
                        ['x', %(values)s],
                        ['OK', %(ok)s],
                        ['Fail', %(fail)s],
                        ['Known', %(known)s]
                    ],
                    types: {
                        OK: 'area',
                        Fail: 'area',
                        Known: 'area',
                        // 'line', 'spline', 'step', 'area', 'area-step' are also available to stack
                    },
                    groups: [['OK', 'Fail', 'Known']],
                    colors: {
                        'OK': 'rgba(31, 239, 184, 0.7)',
                        'Fail': 'rgba(241, 88, 88, 0.7)',
                        'Known': 'rgba(137, 182, 239, 0.7)'
                    }
                },
                axis: {
                    x: {
                        type: 'category'
                    },
                    y: {
                        label: "Tests",
                        tick: {
                            format: function (d) {
                                return (parseInt(d) == d) ? d : null;
                            },
                        }
                    }
                }
            });
        };
        """
        script = script % {
            "ok": ",".join([str(c) for c in data["chart"]["ok"]]),
            "fail": ",".join([str(c) for c in data["chart"]["fail"]]),
            "known": ",".join([str(c) for c in data["chart"]["known"]]),
            "values": ",".join([f"'{str(c)}'" for c in data["chart"]["x"]])
        }

        s = (
            '\n\n## Chart\n\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/5.15.0/d3.min.js"></script>\n'
            '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/c3/0.7.12/c3.min.css">\n'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/c3/0.7.12/c3.min.js"></script>\n'
            '<div><div id="data-chart"></div></div>\n'
            '<script>\n'
            f'{script}\n'
            '</script>'
        )
        return s

    def format(self, data):
        body = self.format_metadata(data)
        body += self.format_reference(data)
        body += self.format_chart(data)
        body += self.format_table(data)
        return template.strip() % {
            "title": "Results",
            "logo": self.format_logo(data),
            "confidential": self.format_confidential(data),
            "copyright": self.format_copyright(data),
            "body": body
        }

class Handler(HandlerBase):
    Formatter = NotImplementedError

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--log", metavar="pattern", type=argtype.logfile("r", bufsize=1, encoding="utf-8"),
            nargs="+", help="log file pattern", required=True)
        parser.add_argument("--log-link", metavar="attribute",
            help="attribute that is used as a link for the log, default: job.url",
            type=str, default="job.url")
        parser.add_argument("--only", metavar="pattern", nargs="+",
            help="compare only selected tests", type=str, required=False)
        parser.add_argument("--order-by", metavar="attribute", type=str,
            help="attribute that is used to order the logs")
        parser.add_argument("--sort", metavar="direction", type=str,
            help="sort direction. Either 'asc' or 'desc', default: asc", choices=["asc", "desc"], default="asc")
        parser.add_argument("--format", metavar="type", type=str,
            help="output format, default: md (Markdown)", choices=["md"], default="md")
        parser.add_argument("output", metavar="output", type=argtype.file("w", bufsize=1, encoding="utf-8"),
            nargs="?", help='output file, default: stdout', default="-")
        parser.add_argument("--copyright", metavar="name", help="add copyright notice", type=str)
        parser.add_argument("--confidential", help="mark as confidential", action="store_true")
        parser.add_argument("--logo", metavar="path", type=argtype.file("rb"),
                help='use logo image (.png)')

    def chart(self, counts):
        chart = {
            "ok": [],
            "fail": [],
            "known": [],
            "x": []
        }
        for counts in reversed(list(counts.values())):
            chart["ok"].append(counts.ok)
            chart["fail"].append(counts.fail + counts.error + counts.null)
            chart["known"].append(counts.xok + counts.xfail + counts.xerror + counts.xnull)
            chart["x"].append(counts.reference)
        return chart

    def get_attribute(self, result, name, default=None):
        tests = list(result["tests"].values())

        if not tests:
            return default

        test = tests[0]["test"]
        for attr in test["attributes"]:
            if attr["attribute_name"] == name:
                return attr["attribute_value"]

        return default

    def filter(self, tests, only):
        if not only:
            return tests

        filters = []
        for pattern in only:
            filters.append(The(pattern).at(sep))

        _tests = []
        for test in tests:
            match = False
            for filter in filters:
                if filter.match(test, prefix=False):
                    match = True
                    break
            if match:
                _tests.append(test)

        return _tests

    def counts(self, tests, results):
        results_counts = {}
        for log, result in results.items():
            results_counts[log] = Counts("tests", *([0] * 11))
            _counts = results_counts[log]
            _counts.reference = result["reference"]

            for testname in tests:
                test = result["tests"].get(testname)
                if test and test.get("result"):
                    if not test["result"].get("result_type"):
                        raise ValueError(f"no result for '{test['test']['test_name']}'")
                    _name = test["result"]["result_type"].lower()
                    setattr(_counts, _name, getattr(_counts, _name) + 1)
                _counts.units += 1

        return results_counts

    def sort(self, results, order_by=None, direction="asc"):
        _results = {}

        def order_key(v):
            started = results[v].get("started", 0)
            if order_by:
                value = "-"
                if results[v].get("tests"):
                    value = self.get_attribute(results[v], order_by, value)
                return [value, started]
            return [started]

        key_order = sorted(results, key=order_key, reverse=True)

        if direction == "desc":
            key_order = reversed(key_order)

        for i, key in enumerate(key_order):
            _results[key] = results[key]
            ref = order_key(key)
            ref[-1] = f'{localfromtimestamp(ref[-1]):%b %d, %-H:%M}'
            if order_by:
                ref = f'{ref[0]}, {ref[-1]}'
            else:
                ref = ref[-1]
            _results[key]["reference"] = ref
        return _results

    def tests(self, results):
        tests = []
        for r in results.values():
            for uname, test in r["tests"].items():
                if getattr(TestType, test["test"]["test_type"]) < TestType.Test:
                    continue
                if test["test"].get("test_parent_type"):
                    if getattr(TestType, test["test"]["test_parent_type"]) < TestType.Suite:
                        continue
                if Flags(test["test"]["test_cflags"]) & RETRY:
                    continue
                tests.append(uname)
        return human(list(set(tests)))

    def table(self, tests, results, ref_link=None):
        table = {
            "header": ["Test Name"] + [f'<a href="#ref-{results[r]["reference"]}">{results[r]["reference"]}</a>' for r in results],
            "rows": [],
            "reference": {
                "header": ["Reference", "Link"],
                "rows": [[f'<span id="ref-{results[r]["reference"]}"><strong>{results[r]["reference"]}</strong></span>', self.get_attribute(results[r], str(ref_link), r)] for r in results]
            },
        }

        if not tests:
            table["rows"].append([""] * len(results.values()))

        for test in tests:
            row = [test]
            for result in results.values():
                if result["tests"].get(test) and result["tests"].get(test).get("result"):
                    row.append(result["tests"].get(test)["result"])
                else:
                    row.append(None)
            table["rows"].append(row)
        return table

    def metadata(self, only, order_by, direction):
        return {
            "date": time.time(),
            "version": __version__,
            "order-by": order_by,
            "sort": direction,
            "filter": (" ".join(only) if only else "None")
        }

    def company(self, args):
        d = {}
        if args.copyright:
            d["name"] = args.copyright
        if args.confidential:
            d["confidential"] = True
        if args.logo:
            d["logo"] = args.logo.read()
        return d

    def data(self, results, args):
        d = dict()
        results = self.sort(results, args.order_by, args.sort)
        d["tests"] = self.filter(self.tests(results), args.only)
        d["table"] = self.table(d["tests"], results, args.log_link)
        d["counts"] = self.counts(d["tests"], results)
        d["chart"] = self.chart(d["counts"])
        d["metadata"] = self.metadata(args.only, args.order_by, args.sort)
        d["company"] = self.company(args)
        return d

    def generate(self, formatter, results, args):
        output = args.output
        output.write(
            formatter.format(self.data(results, args))
        )
        output.write("\n")

    def handle(self, args):
        results = {}
        threads = []

        def thread_worker(log, results):
            ResultsLogPipeline(log, results).run()

        for log in args.log:
            log_results = {}
            threads.append(
                threading.Thread(target=thread_worker, args=(log, log_results))
            )
            results[log.name] = log_results
            threads[-1].start()

        for thread in threads:
            thread.join()

        formatter = self.Formatter()
        self.generate(formatter, results, args)
