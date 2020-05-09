import sys
import traceback

def exception(exc_type=None, exc_value=None, exc_traceback=None):
    """Get exception string.
    """
    if (exc_type, exc_value, exc_traceback) == (None, None, None):
        exc_type, exc_value, exc_traceback  = sys.exc_info()
    return "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)).rstrip()


class TestFlowsException(Exception):
    """Base exception class.
    """
    pass

class ResultException(TestFlowsException):
    """Result exception.
    """
    def __init__(self, result):
        self.result = result

class DummyTestException(TestFlowsException):
    """Dummy test exception.
    """
    pass

class RepeatTestException(TestFlowsException):
    """Repeat test exception.
    """
    pass

class TestFlowsError(TestFlowsException):
    """Base error exception class.
    """
    pass

class RequirementError(TestFlowsError):
    """Requirement error.
    """
    pass

class ArgumentError(TestFlowsError):
    """Argument error.
    """
    pass
