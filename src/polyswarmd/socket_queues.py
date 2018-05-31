import gevent
import gevent.queue
from polyswarmd.eth import web3

# TODO: This needs some tweaking to work for multiple accounts / concurrent
# requests, mostly dealing with nonce calculation
class TransactionQueue(object):
    def __init__(self):
        self.inner = gevent.queue.Queue()
        self.lock = gevent.lock.Semaphore()
        self.dict = dict()
        self.chain_id = int(web3.net.version)
        self.id_ = 0
        self.pending = 0

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def complete(self, id_, txhash):
        self.acquire()
        self.dict[id_].set_result(txhash)
        self.pending -= 1
        self.release()

    def send_transaction(self, call, account):
        self.acquire()

        nonce = web3.eth.getTransactionCount(account) + self.pending
        self.pending += 1

        tx = call.buildTransaction({
            'nonce': nonce,
            'chainId': self.chain_id,
            'gas': 2000000
        })

        result = gevent.event.AsyncResult()
        self.dict[self.id_] = result
        self.inner.put((self.id_, tx))
        self.id_ += 1
        self.release()
        return result

    def __iter__(self):
        return iter(self.inner)

class MessageQueue(object):
    def __init__(self):
        self.inner = gevent.queue.Queue()
        self.lock = gevent.lock.Semaphore()
        self.dict = dict()
        self.id_ = 0
        self.pending = 0

    def acquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()

    def complete(self, id_, msg, account):
        self.acquire()
        self.dict[id_].set_result(msg)
        self.pending -= 1
        self.release()

    def send_message(self, msg, account):
        self.acquire()
        self.pending += 1

        result = gevent.event.AsyncResult()
        self.dict[self.id_] = result
        self.inner.put((self.id_, msg, account))
        self.id_ += 1
        self.release()
        return result

    def __iter__(self):
        return iter(self.inner)
