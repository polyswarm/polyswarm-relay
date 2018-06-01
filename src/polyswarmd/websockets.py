import json

import jsonschema
from jsonschema.exceptions import ValidationError
from flask_sockets import Sockets
import gevent
import gevent.queue
from hexbytes import HexBytes

from polyswarmd.eth import web3, bounty_registry
from polyswarmd.utils import new_bounty_event_to_dict, new_assertion_event_to_dict, new_verdict_event_to_dict
from polyswarmd.socket_queues import MessageQueue, TransactionQueue

transaction_queue = TransactionQueue()

message_queue = MessageQueue()

import websocket
try:
    import thread
except ImportError:
    import _thread as thread

class WebsocketClient(object):
    def __init__(self):
        self.inner = gevent.queue.Queue()
        self.lock = gevent.lock.Semaphore()
        self.dict = dict()
        self.chain_id = int(web3.net.version)
        self.id_ = 0
        self.pending = 0

    def on_message(self, ws, message):
        # send to message queue to be signed
        print('')
        print(send_message)
        print(self.uri)
        print('')
        message_queue.send_message(send_message, self.uri)

    def send(self, message):
        ws.send(message)

    def run(self, uri):
        self.uri = uri
        ws = websocket.WebSocketApp(uri, on_message = self.on_message)
        ws.run_forever()

def init_websockets(app):
    sockets = Sockets(app)

    @sockets.route('/events')
    def events(ws):
        block_filter = web3.eth.filter('latest')
        bounty_filter = bounty_registry.eventFilter('NewBounty')
        assertion_filter = bounty_registry.eventFilter('NewAssertion')
        verdict_filter = bounty_registry.eventFilter('NewVerdict')

        try:
            while not ws.closed:
                for event in block_filter.get_new_entries():
                    ws.send(
                        json.dumps({
                            'event': 'block',
                            'data': {
                                'number': web3.eth.blockNumber,
                            },
                        }))

                for event in bounty_filter.get_new_entries():
                    ws.send(
                        json.dumps({
                            'event':
                            'bounty',
                            'data':
                            new_bounty_event_to_dict(event.args),
                        }))

                for event in assertion_filter.get_new_entries():
                    ws.send(
                        json.dumps({
                            'event':
                            'assertion',
                            'data':
                            new_assertion_event_to_dict(event.args),
                        }))

                for event in verdict_filter.get_new_entries():
                    ws.send(
                        json.dumps({
                            'event':
                            'verdict',
                            'data':
                            new_verdict_event_to_dict(event.args),
                        }))

                gevent.sleep(1)
        except:
            pass

    @sockets.route('/transactions')
    def transactions(ws):
        def queue_greenlet():
            for (id_, tx) in transaction_queue:
                ws.send(json.dumps({'id': id_, 'data': tx}))

        qgl = gevent.spawn(queue_greenlet)

        schema = {
            'type': 'object',
            'properties': {
                'id': {
                    'type': 'integer',
                },
                'data': {
                    'type': 'string',
                    'maxLength': 4096,
                },
            },
            'required': ['id', 'data'],
        }

        try:
            while not ws.closed:
                msg = ws.receive()
                if not msg:
                    break

                body = json.loads(msg)
                try:
                    jsonschema.validate(body, schema)
                except ValidationError as e:
                    print('Invalid JSON: ' + e.message)

                id_ = body['id']
                data = body['data']

                txhash = web3.eth.sendRawTransaction(HexBytes(data))
                print('GOT TXHASH:', txhash)
                transaction_queue.complete(id_, txhash)

        finally:
            qgl.kill()

    @sockets.route('/messages')
    def messages(ws):
        def queue_greenlet():
            for (id_, msg, uri) in message_queue:
                ws.send(json.dumps({'id': id_, 'data': msg, 'uri': uri}))

        qgl = gevent.spawn(queue_greenlet)
        # message state object
        schema = {
            'type': 'object',
            'properties': {
                'type': {
                    'type': 'string',
                },
                'state': {
                    'type': 'string',
                    'minLength': 32,
                },
                'r': {
                    'type': 'string',
                    'minLength': 64,
                },
                'v': {
                    'type': 'integer',
                    'minimum': 0,
                },
                's': {
                    'type': 'string',
                    'minLength': 64
                },
            },
            'required': ['type', 'state', 'r', 'v', 's'],
        }

        try:
            while not ws.closed:
                msg = ws.receive()
                if not msg:
                    break

                body = json.loads(msg)
                try:
                    jsonschema.validate(body, schema)
                except ValidationError as e:
                    print('Invalid JSON: ' + e.message)

                if body['uri']:
                    ws = create_connection(body['uri'])
                    ws.send(body['data'])
                    ws.close()

                    message_queue.complete(_id, state)

        finally:
            qgl.kill()
