import uuid

import jsonschema
from jsonschema.exceptions import ValidationError

from flask import Blueprint, request

from polyswarmd import eth
from polyswarmd.artifacts import is_valid_ipfshash
from polyswarmd.eth import web3, check_transaction, nectar_token, offer_registry, bind_contract, zero_address, offer_msig_json
from polyswarmd.response import success, failure
from polyswarmd.websockets import transaction_queue
from polyswarmd.utils import bool_list_to_int, bounty_to_dict, assertion_to_dict, new_bounty_event_to_dict, new_assertion_event_to_dict, new_verdict_event_to_dict, new_offer_contract_event_to_dict

offers = Blueprint('offers', __name__)

@offers.route('', methods=['POST'])
def create_offer_channel():
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    body = request.get_json()

    schema = {
        'type': 'object',
        'properties': {
            'ambassador': {
                'type': 'string',
                'minLength': 42,
            },
            'expert': {
                'type': 'string',
                'minLength': 42,
            },
            'settlementPeriodLength': {
                'type': 'integer',
                'minimum': 0,
            },
            'public_eth_uri': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 32
            }
        },
        'required': ['ambassador', 'expert', 'settlementPeriodLength', 'public_eth_uri'],
    }

    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    guid = uuid.uuid4()
    ambassador = web3.toChecksumAddress(body['ambassador'])
    expert = web3.toChecksumAddress(body['expert'])
    settlementPeriodLength = body['settlementPeriodLength']
    public_eth_uri = body['public_eth_uri']

    tx = transaction_queue.send_transaction(
        offer_registry.functions.initializeOfferChannel(guid.int, ambassador, expert, settlementPeriodLength),
        account).get()

    if not check_transaction(tx):
        return failure(
            'The offer contract deploy transaction failed, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.InitializedChannel().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    success_dict = dict(processed[0]['args'])

    msig_address = success_dict['msig'] 

    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.setCommunicationUri(web3.toBytes(text = public_eth_uri)),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to set to set socket url verify parameters and use the setWebsocket/ endpoint to try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_msig.events.CommunicationsSet().processReceipt(receipt)

    # TODO: Fix encoding
    success_dict['websocketUri'] = dict(processed[0]['args'])['websocketUri']

    # convert to string for javascipt
    success_dict['guid'] = str(success_dict['guid'])

    return success(success_dict)


@offers.route('/<int:guid>/open', methods=['POST'])
def open(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    offer_channel = new_offer_contract_event_to_dict(offer_registry.functions.guidToChannel(guid).call())
    msig_address = offer_channel['msig_address']

    body = request.get_json()

    schema = {
        'type': 'object',
        'properties': {
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
            }
        },
        'required': ['state', 'r', 'v', 's'],
    }

    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    state = body['state']
    v = body['v']
    r = body['r']
    s = body['s']

    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        nectar_token.functions.approve(offer_msig_address.address, approveAmount),
        account).get()
    if not check_transaction(tx):
        return failure(
            'Approve transaction failed, verify parameters and try again', 400)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.openAgreement(state, v, r, s),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to open agreement, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.OpenedAgreement().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    data = dict(processed[0]['args'])

    return success(data)

@offers.route('/<int:guid>/join', methods=['POST'])
def join(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    offer_channel = new_offer_contract_event_to_dict(offer_registry.functions.guidToChannel(guid).call())
    msig_address = offer_channel['msig_address']

    body = request.get_json()

    schema = {
        'type': 'object',
        'properties': {
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
            }
        },
        'required': ['state', 'r', 'v', 's'],
    }

    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    state = body['state']
    v = body['v']
    r = body['r']
    s = body['s']

    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.joinAgreement(state, v, r, s),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to open agreement, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.JoinedAgreement().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    data = dict(processed[0]['args'])

    return success(data)

@offers.route('/<int:guid>/close', methods=['POST'])
def close(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    offer_channel = new_offer_contract_event_to_dict(offer_registry.functions.guidToChannel(guid).call())
    msig_address = offer_channel['msig_address']

    body = request.get_json()
    
    schema = {
        'type': 'object',
        'properties': {
            'state': {
                'type': 'string',
                'minLength': 32,
            },
            'r': {
                'type': 'list',
                'minLength': 2,
            },
            'v': {
                'type': 'list',
                'minimum': 2,
            },
            's': {
                'type': 'list',
                'minLength': 2
            }
        },
        'required': ['state', 'r', 'v', 's'],
    }

    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    state = body['state']
    v = body['v']
    r = body['r']
    s = body['s']


    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.closeAgreement(state, v, r, s),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to open agreement, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.ClosedAgreement().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    data = dict(processed[0]['args'])

    return success(data)


@offers.route('/<int:guid>/settle', methods=['POST'])
def settle(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)
    offer_channel = new_offer_contract_event_to_dict(offer_registry.functions.guidToChannel(guid).call())
    msig_address = offer_channel['msig_address']

    body = request.get_json()

    schema = {
        'type': 'object',
        'properties': {
            'state': {
                'type': 'string',
                'minLength': 32,
            },
            'r': {
                'type': 'list',
                'minLength': 2,
            },
            'v': {
                'type': 'list',
                'minimum': 2,
            },
            's': {
                'type': 'list',
                'minLength': 2
            }
        },
        'required': ['state', 'r', 'v', 's'],
    }

    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    state = body['state']
    v = body['v']
    r = body['r']
    s = body['s']

    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.startSettle(state, v, r, s),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to open agreement, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.StartedSettle().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    data = dict(processed[0]['args'])

    return success(data)

@offers.route('/<int:guid>/challenge', methods=['POST'])
def challange(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    offer_channel = new_offer_contract_event_to_dict(offer_registry.functions.guidToChannel(guid).call())
    msig_address = offer_channel['msig_address']

    body = request.get_json()

    schema = {
        'type': 'object',
        'properties': {
            'state': {
                'type': 'string',
                'minLength': 32,
            },
            'r': {
                'type': 'list',
                'minLength': 2,
            },
            'v': {
                'type': 'list',
                'minimum': 2,
            },
            's': {
                'type': 'list',
                'minLength': 2
            }
        },
        'required': ['state', 'r', 'v', 's'],
    }


    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message)

    state = body['state']
    v = body['v']
    r = body['r']
    s = body['s']


    offer_msig = bind_contract(msig_address, offer_msig_json)

    tx = transaction_queue.send_transaction(
        offer_msig.functions.challengeSettle(state, v, r, s),
        account).get()

    if not check_transaction(tx):
        return failure(
            'Failed to open agreement, verify parameters and try again', 400)

    receipt = web3.eth.getTransactionReceipt(tx)

    processed = offer_registry.events.SettleStateChallenged().processReceipt(receipt)

    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)

    data = dict(processed[0]['args'])

    return success(data)

@offers.route('/<int:guid>', methods=['GET'])
def get_channel_address(guid):
    offer_channel = offer_registry.functions.guidToChannel(guid).call()

    return success({ 'offer_channel': new_offer_contract_event_to_dict(offer_channel) })

@offers.route('/<int:guid>/settlementPeriod', methods=['GET'])
def get_settlement_period(guid):
    offer_channel = offer_registry.functions.guidToChannel(guid).call()
    offer_msig = bind_contract(msig_address, offer_msig_json)

    settlementPeriodEnd = offer_msig.functions.settlementPeriodEnd().call()

    return success({ 'settlementPeriodEnd': settlementPeriodEnd })

@offers.route('pending', methods=['GET'])
def pending():
    offers_pending = []
    offer_channel = offer_registry.functions.guidToChannel(guid).call()
    offer_msig = bind_contract(msig_address, offer_msig_json)
    num_of_offers = offer_registry.functions.getNumberOfOffers().call()

    for i in range(0, num_of_offers):
        guid = offer_registry.functions.channelsGuids(i).call()
        channel_address = offer_registry.guidToChannel(guid).call()
        offer_msig = bind_contract(channel_address, offer_msig_json)
        pending = offer_msig.functions.isPending().call()
        if pending:
            offers_pending.append({ 'guid': guid, 'address': channel_address })

    return success(offers_pending)

@offers.route('opened', methods=['GET'])
def opened(guid):
    offers_opened = []
    offer_channel = offer_registry.functions.guidToChannel(guid).call()
    offer_msig = bind_contract(msig_address, offer_msig_json)
    num_of_offers = offer_registry.functions.getNumberOfOffers().call()

    for i in range(0, num_of_offers):
        guid = offer_registry.functions.channelsGuids(i).call()
        channel_address = offer_registry.guidToChannel(guid).call()
        offer_msig = bind_contract(channel_address, offer_msig_json)
        pending = offer_msig.functions.isOpen().call()
        if pending:
            offers_opened.append({ 'guid': guid, 'address': channel_address })

    return success(offers_opened)

@offers.route('closed', methods=['GET'])
def closed(guid):
    offers_closed = []
    offer_channel = offer_registry.functions.guidToChannel(guid).call()
    offer_msig = bind_contract(msig_address, offer_msig_json)
    num_of_offers = offer_registry.functions.getNumberOfOffers().call()

    for i in range(0, num_of_offers):
        guid = offer_registry.functions.channelsGuids(i).call()
        channel_address = offer_registry.guidToChannel(guid).call()
        offer_msig = bind_contract(channel_address, offer_msig_json)
        pending = offer_msig.functions.isClosed().call()
        if pending:
            offers_closed.append({ 'guid': guid, 'address': channel_address })

    return success(offers_closed)

@offers.route('myoffers', methods=['GET'])
def myoffers(guid):
    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    my_offers = []
    offer_channel = offer_registry.functions.guidToChannel(guid).call()
    offer_msig = bind_contract(msig_address, offer_msig_json)
    num_of_offers = offer_registry.functions.getNumberOfOffers().call()

    for i in range(0, num_of_offers):
        guid = offer_registry.functions.channelsGuids(i).call()
        channel_address = offer_registry.guidToChannel(guid).call()
        offer_msig = bind_contract(channel_address, offer_msig_json)
        expert = offer_msig.functions.expert().call()
        ambassador = offer_msig.functions.ambassador().call()
        if account is expert or account is ambassador:
            my_offers.append({ 'guid': guid, 'address': channel_address })

    return success(my_offers)
