# Copyright 2019 Vitaliy Zakaznikov (TestFlows Test Framework http://testflows.com)
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
import json

from datetime import datetime

import testflows.settings as settings
import testflows._core.cli.arg.type as argtype

from testflows._core.flags import Flags, SKIP
from testflows._core.testtype import TestType
from testflows._core.transform.log.message import message_map
from testflows._core.cli.arg.common import epilog
from testflows._core.cli.arg.common import HelpFormatter
from testflows._core.cli.arg.handlers.handler import Handler as HandlerBase
from testflows._core.transform.log.pipeline import ResultsLogPipeline
from testflows._core.utils.timefuncs import localfromtimestamp, strftimedelta

template = """
# Test Report
%(body)s
  
---
Generated by <span class="testflows-logo"></span> [<span class="logo-test">Test</span><span class="logo-flows">Flows</span>] Open-Source Test Framework

[<span class="logo-test">Test</span><span class="logo-flows">Flows</span>]: https://testflows.com
"""

results_order =  ["Skip", "OK", "Fail", "Error", "Null", "XOK", "XFail", "XError", "XNull"]

class Handler(HandlerBase):
    @classmethod
    def add_command(cls, commands):
        parser = commands.add_parser("official", help="official test report", epilog=epilog(),
            description="Generate official test report.",
            formatter_class=HelpFormatter)

        parser.add_argument("input", metavar="input", type=argtype.file("r", bufsize=1, encoding="utf-8"),
                nargs="?", help="input log, default: stdin", default="-")
        parser.add_argument("output", metavar="output", type=argtype.file("w", bufsize=1, encoding="utf-8"),
                nargs="?", help='output file, default: stdout', default="-")
        parser.add_argument("-a", "--artifacts", metavar="link", type=str, help='link to the artifacts')

        parser.set_defaults(func=cls())

    def version_section(self, results):
        s = (
            "\n\n"
            f"**Date** {localfromtimestamp(results['started']):%b %d, %Y %-H:%M}  \n"
            f"**Framework** {results['version']}  \n"
        )
        return s

    def summary_chart_section(self, results):
        counts = results["counts"]

        units = (counts["module"].units + counts["suite"].units + counts["test"].units
            + counts["feature"].units + counts["scenario"].units)
        passed = (counts["module"].ok + counts["suite"].ok + counts["test"].ok
            + counts["feature"].ok + counts["scenario"].ok)
        def xout_counts(testtype):
            return counts[testtype].xok + counts[testtype].xfail + counts[testtype].xerror + counts[testtype].xnull
        xout = (xout_counts("module") + xout_counts("suite") + xout_counts("test")
            + xout_counts("feature") + xout_counts("scenario"))
        failed = (counts["module"].fail + counts["suite"].fail + counts["test"].fail
            + counts["feature"].fail + counts["scenario"].fail)
        nulled = (counts["module"].null + counts["suite"].null + counts["test"].null
            + counts["feature"].null + counts["scenario"].null)
        errored = (counts["module"].error + counts["suite"].error + counts["test"].error
            + counts["feature"].error + counts["scenario"].error)
        skipped = (counts["module"].skip + counts["suite"].skip + counts["test"].skip
            + counts["feature"].skip + counts["scenario"].skip)

        def template(value, title, color):
            return (
                f'<div class="c100 p{value} {color}">'
                    f'<span>{value}%</span>'
                    f'<span class="title">{title}</span>'
                    '<div class="slice">'
                        '<div class="bar"></div>'
                        '<div class="fill"></div>'
                    '</div>'
                '</div>\n')
        s = "\n## Summary\n"
        if units <= 0:
            s += "No tests"
        else:
            s += '<div class="chart">'
            if settings.show_skipped:
                if skipped > 0:
                    s += template(f"{skipped / float(units) * 100:.0f}", "Skip", "gray")
            if passed > 0:
                s += template(f"{passed / float(units) * 100:.0f}", "OK", "green")
            if xout > 0:
                s += template(f"{xout / float(units) * 100:.0f}", "XOut", "")
            if failed > 0:
                s += template(f"{failed / float(units) * 100:.0f}", "Fail", "red")
            if errored > 0:
                s += template(f"{errored / float(units) * 100:.0f}", "Error", "orange")
            if nulled > 0:
                s += template(f"{nulled / float(units) * 100:.0f}", "Null", "purple")
            s += '</div>'
        return s

    def statistics_section(self, result):
        s = "\n\n## Statistics\n"
        counts = result["counts"]

        statistics = {"types":{}}

        if counts["module"]:
            statistics["types"]["module"] = counts["module"].__data__()
        if counts["suite"]:
            statistics["types"]["suite"] = counts["suite"].__data__()
        if counts["test"]:
            statistics["types"]["test"] = counts["test"].__data__()
        if counts["feature"]:
            statistics["types"]["feature"] = counts["feature"].__data__()
        if counts["scenario"]:
            statistics["types"]["scenario"] = counts["scenario"].__data__()
        if counts["iteration"]:
            statistics["types"]["iteration"] = counts["iteration"].__data__()
        if counts["step"]:
            statistics["types"]["step"] = counts["step"].__data__()
        fields = set()
        for k in statistics["types"].values():
            fields = fields.union(set(k["counts"].keys()))
        statistics["result_fields"] = []

        for r in results_order:
            if r in fields:
                statistics["result_fields"].append(r)

        fields = ["<span></span>", "Units"] + [f'<span class="result result-{f.lower()}">{f}</span>'for f in statistics["result_fields"]]
        s += " | ".join(fields) + "\n"
        s += " | ".join(["---"] * len(fields)) + "\n"
        for t in statistics["types"]:
            type_data = statistics["types"][t]
            c = [f'{t.capitalize()}s', f'<center>{str(type_data["units"])}</center>']
            for r in statistics["result_fields"]:
                if type_data["counts"].get(r):
                    c.append(f'<center>{str(type_data["counts"][r])}</center>')
                else:
                    c.append("")
            s += " | ".join(c) + "\n"
        return s + "\n"

    def results_section(self, results):
        s = "\n## Results\n"
        s += (
            'Test Name | Result | <span style="display: block; min-width: 100px;">Duration</span>\n'
            "--- | --- | --- \n"
        )
        for test in results["tests"].values():
            result = test["result"]
            if result.p_type < TestType.Test:
                continue
            flags = Flags(result.p_flags)
            if flags & SKIP and settings.show_skipped is False:
                continue
            cls = result.name.lower()
            s += " | ".join([result.test, f'<span class="result result-{cls}">{result.name}</span>', strftimedelta(result.p_time)]) + "\n"
        return s

    def artifacts_section(self, link):
        s = "\n## Artifacts\n"
        name = link.lstrip("./")
        s += f"Test artifacts can be found at "
        if link.startswith("http"):
            s += f"{link}\n"
        else:
            s += f"[{name}]({link})\n"
        return s

    def attributes_and_tags_section(self, results):
        s = ""
        if not results["tests"]:
            return s
        test = next(iter(results["tests"].values()), None)["test"]

        if test.attributes:
            s += "\n\n### Attributes\n"
            s += "<table>\n"
            for attr in test.attributes:
                s += f'<tr><td><strong>{attr.name}</strong></td><td>{attr.value}</td></tr>\n'
            s += "</table>\n"
        if test.tags:
            s += "\n\n### Tags\n"
            s += "<table>\n<tr>"
            for i, tag in enumerate(test.tags):
                if i > 0 and i % 5 == 0:
                    s += "</tr><tr>"
                s += f'<td><strong class="tag tag-{i % 5}">{tag.value}</strong></td>'
            s += "</tr>\n</table>\n"
        return s

    def generate(self, results, args):
        output = args.output
        artifacts = args.artifacts

        body = ""
        body += self.version_section(results)
        body += self.attributes_and_tags_section(results)
        if artifacts:
            body += self.artifacts_section(artifacts)
        body += self.summary_chart_section(results)
        body += self.statistics_section(results)
        body += self.results_section(results)
        output.write(template.strip() % {"body": body})
        output.write("\n")

    def handle(self, args):
        results = {}
        ResultsLogPipeline(args.input, results).run()
        self.generate(results, args)
