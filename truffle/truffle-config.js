require('babel-register');
require('babel-polyfill');

module.exports = {
  networks: {
    development: {
      host: 'localhost',
      port: 8545,
      network_id: '*',
    },
    sidechain: {
      host: 'localhost',
      port: 7545,
      network_id: '*',
    }
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
