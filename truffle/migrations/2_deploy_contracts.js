const NectarToken = artifacts.require('NectarToken');
const ERC20Relay = artifacts.require('ERC20Relay');

module.exports = function(deployer, network, accounts) {
  // https://etherscan.io/token/0x9e46a38f5daabe8683e10793b06749eef7d733d1#readContract totalSupply
  const TOTAL_SUPPLY = '1885913075851542181982426285';

  // https://coinmarketcap.com/currencies/polyswarm/ retrieved on 5/28/18
  const NCT_ETH_EXCHANGE_RATE = 80972;

  // See docker setup
  const FEE_WALLET = '0x0f57baedcf2c84383492d1ea700835ce2492c48a';
  const VERIFIER_ADDRESSES = [
    '0x31c99a06cabed34f97a78742225f4594d1d16677',
    '0x6aae54b496479a25cacb63aa9dc1e578412ee68c',
    '0x850a2f35553f8a79da068323cbc7c9e1842585d5',
  ];

  if (network === 'mainnet') {
    const NECTAR_ADDRESS = '0x9e46a38f5daabe8683e10793b06749eef7d733d1';
    // XXX: Change me
    const MAINNET_FEE_WALLET = '0x0f57baedcf2c84383492d1ea700835ce2492c48a';

    return deployer.deploy(ERC20Relay, NECTAR_ADDRESS, NCT_ETH_EXCHANGE_RATE,
      FEE_WALLET, VERIFIER_ADDRESSES);
  } else {
    return deployer.deploy(NectarToken).then(() => {
      return deployer.deploy(ERC20Relay, NectarToken.address, NCT_ETH_EXCHANGE_RATE,
        FEE_WALLET, VERIFIER_ADDRESSES).then(() => {

        // If we're on the homechain, assign all tokens to the user, else assign
        // all tokens to the relay contract for disbursal on the sidechain
        //
        // Else for testing purposes, give both the user and the relay tokens
        if (network === 'homechain') {
          return NectarToken.deployed().then(token => {
            return token.mint(accounts[0], TOTAL_SUPPLY);
          });
        } else if (network == 'sidechcain') {
          return NectarToken.deployed().then(token => {
            return token.mint(ERC20Relay.address, TOTAL_SUPPLY);
          });
        } else if (network == 'development') {
          return NectarToken.deployed().then(token => {
            return token.mint(accounts[0], TOTAL_SUPPLY).then(() => {;
              return token.mint(ERC20Relay.address, TOTAL_SUPPLY);
            });
          });
        }
      });
    });
  }
};
