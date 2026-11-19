"""Coalesced requests to the existing session collector, without signals."""
import time
from .language import tr


def request_collection(worker,path):
    if worker.poll() is not None:
        raise RuntimeError(tr('Collector stopped. Close and reopen the panel.'))
    path.touch(mode=0o600)
    return tr('Collection requested. Waiting for the collector.')


def wait_for_collection(path,seconds):
    deadline=time.monotonic()+seconds
    while not path.exists():
        remaining=deadline-time.monotonic()
        if remaining<=0:return
        time.sleep(min(.1,remaining))
