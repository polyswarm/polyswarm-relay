import jsonschema
from jsonschema.exceptions import ValidationError

from flask import Blueprint, request

from polyswarmd.response import success, failure
from polyswarmd.eth import web3 as web3_chains, check_transaction, nectar_token as nectar_chains, erc20_relay_address as erc20_chains
from polyswarmd.websockets import transaction_queue as transaction_chains
from polyswarmd.utils import new_transfer_event_to_dict

relay = Blueprint('relay', __name__)

@relay.route('/deposit', methods=['POST'])
def deposit_funds():
    # Move funds from home to side
    return send_funds_from('home')

@relay.route('/withdrawal', methods=['POST'])
def withdraw_funds():
    # Move funds from side to home
    return send_funds_from('side')

def send_funds_from(chain):
    # Grab correct versions by chain type
    web3 = web3_chains[chain]
    nectar_token = nectar_chains[chain]
    erc20_relay_address = erc20_chains[chain]
    transaction_queue = transaction_chains[chain]

    account = request.args.get('account')
    if not account or not web3.isAddress(account):
        return failure('Source account required', 401)
    account = web3.toChecksumAddress(account)

    if not erc20_relay_address or not web3.isAddress(erc20_relay_address):
        return failure('ERC20 Relay misconfigured', 500)
    erc20_relay_address = web3.toChecksumAddress(erc20_relay_address)

    schema = {
        'type': 'object',
        'properties': {
            'amount': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 64,
                'pattern': r'^\d+$',
            },
        },
        'required': ['amount'],
    }

    body = request.get_json()
    try:
        jsonschema.validate(body, schema)
    except ValidationError as e:
        return failure('Invalid JSON: ' + e.message, 400)

    amount = int(body['amount'])

    tx = transaction_queue.send_transaction(
        nectar_token.functions.transfer(erc20_relay_address, amount),
        account).get()
    
    if not check_transaction(web3, tx):
        return failure(
            'Approve transaction failed, verify parameters and try again', 400)
    receipt = web3.eth.getTransactionReceipt(tx)
    processed = nectar_token.events.Transfer().processReceipt(receipt)
    if not processed:
        return failure(
            'Invalid transaction receipt, no events emitted. Check contract addresses',
            400)
    new_transfer_event = processed[0]['args']
    return success(new_transfer_event_to_dict(new_transfer_event))