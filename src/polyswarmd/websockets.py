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

    @sockets.route('/ambassadorSigned')
    def ambassador_messages(ws):
        def queue_greenlet():
            for (id_, msg, account) in message_queue:
                # check guid and send to correct expert here
                ws.send(json.dumps({'id': id_, 'data': msg, 'account': account}))

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

                state = body['state']
                account = body['account']


                message_queue.complete(state, account)

        finally:
            qgl.kill()

    @sockets.route('/expertSigned')
    def expert_messages(ws):
        def queue_greenlet():
            for (id_, msg, account) in message_queue:
                # check guid and send to correct socket uri here
                ws.send(json.dumps({'id': id_, 'data': msg, 'account': account}))

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

                state = body['state']
                account = body['account']


                message_queue.complete(state, account)

        finally:
            qgl.kill()
