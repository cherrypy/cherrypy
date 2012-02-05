
class Timer:
    "stubbed"
class NeverExpires:
    "stubbed"
class LockTimeout:
    "stubbed"

class LockChecker(object):
    """
    Keep track of the time and detect if a timeout has expired
    """
    def __init__(self, session_id, timeout):
        self.session_id = session_id
        if timeout:
            self.timer = Timer.after(timeout)
        else:
            self.timer = NeverExpires()

    def expired(self):
        if self.timer.expired():
            raise LockTimeout(
                "Timeout acquiring lock for %(session_id)s" % vars(self))
        return False
