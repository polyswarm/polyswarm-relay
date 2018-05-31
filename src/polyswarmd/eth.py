import json
import os

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

from polyswarmd.config import eth_uri, nectar_token_address, bounty_registry_address, whereami

web3 = Web3(HTTPProvider(eth_uri))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


def bind_contract(address, artifact):
    with open(os.path.abspath(os.path.join(whereami(), artifact)), 'r') as f:
        abi = json.load(f)['abi']

    return web3.eth.contract(address=web3.toChecksumAddress(address), abi=abi)


zero_address = '0x0000000000000000000000000000000000000000'

nectar_token = bind_contract(nectar_token_address,
                             os.path.join('truffle', 'build', 'contracts',
                                          'NectarToken.json'))

bounty_registry = bind_contract(bounty_registry_address,
                                os.path.join('truffle', 'build', 'contracts',
                                             'BountyRegistry.json'))


def check_transaction(tx):
    receipt = web3.eth.waitForTransactionReceipt(tx)
    return receipt and receipt.status == 1


def is_arbiter(account):
    return bounty_registry.call().isArbiter(account)


def bounty_fee():
    return bounty_registry.call().BOUNTY_FEE()


def assertion_fee():
    return bounty_registry.call().ASSERTION_FEE()


def bounty_amount_min():
    return bounty_registry.call().BOUNTY_AMOUNT_MINIMUM()


def assertion_bid_min():
    return bounty_registry.call().ASSERTION_BID_MINIMUM()
