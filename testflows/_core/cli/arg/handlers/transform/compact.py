# Copyright 2019 Katteli Inc.
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
import testflows._core.cli.arg.type as argtype

from testflows._core.cli.arg.common import epilog
from testflows._core.cli.arg.common import HelpFormatter
from testflows._core.cli.arg.handlers.handler import Handler as HandlerBase
from testflows._core.transform.log.pipeline import CompactRawLogPipeline

class Handler(HandlerBase):
    @classmethod
    def add_command(cls, commands):
        parser = commands.add_parser("compact", help="compact transform", epilog=epilog(),
            description="Transform log into compact raw log containing only test results.",
            formatter_class=HelpFormatter)

        parser.add_argument("--with-steps", action="store_true", help="include test steps, default: True", default=True)
        parser.add_argument("--without-steps", action="store_true", help="exclude test steps, default: False", default=False)
        parser.add_argument("input", metavar="input", type=argtype.logfile("r", bufsize=1, encoding="utf-8"),
                nargs="?", help="input log, default: stdin", default="-")
        parser.add_argument("output", metavar="output", type=argtype.logfile("w", bufsize=1, encoding="utf-8"),
                nargs="?", help='output file, default: stdout', default="-")

        parser.set_defaults(func=cls())

    def handle(self, args):
        with args.output:
            CompactRawLogPipeline(args.input, args.output, steps=(not args.without_steps)).run()