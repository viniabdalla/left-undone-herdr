"""Coalesced requests to the existing session collector, without signals."""
import time


def request_collection(worker,path):
    if worker.poll() is not None:
        raise RuntimeError('Coletor parou. Feche e reabra o painel.')
    path.touch(mode=0o600)
    return 'Coleta solicitada. Aguarde o status do coletor.'


def wait_for_collection(path,seconds):
    deadline=time.monotonic()+seconds
    while not path.exists():
        remaining=deadline-time.monotonic()
        if remaining<=0:return
        time.sleep(min(.1,remaining))
