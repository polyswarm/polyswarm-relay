require('babel-register');
require('babel-polyfill');

module.exports = {
  networks: {
    development: {
      host: 'geth',
      port: 8545,
      network_id: '*',
      gas: 4700000,
    },
    rinkeby: {
      host: 'localhost',
      port: 8545,
      network_id: '4',
    },
    mainnet: {
      host: 'localhost',
      port: 8545,
      network_id: '1',
    },
  },
  solc: {
    optimizer: {
      enabled: true,
      runs: 200
    }
  }
};
