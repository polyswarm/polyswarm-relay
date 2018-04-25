extern crate web3;
extern crate ethabi;

use web3::futures::{Future, Stream};
use web3::types::{FilterBuilder, H256, Bytes, Address, U256};
use web3::contract::{Contract, Options};
use web3::transports::ws::WebSocket;
use web3::api::Web3;
use ethabi::{EventParam, Event, ParamType, Hash};
use std::sync::{mpsc, Arc, Mutex};
use std::{thread};
use std::fs::File;

#[derive(Clone)]
pub struct Bridge {
    wallet: Address,
    password: String,
    contract: ethabi::Contract,
    main: Network,
    side: Network,
}

impl Bridge {
    pub fn new(wallet: &str, password: &str, abi_path: &str, main: Network, side: Network) -> Bridge {
        let start = match wallet.starts_with("0x") {
            true => 2,
            false => 0
        };
        let verifier_wallet: Address = wallet[start..40+start].parse().expect("Invalid verifier address.");
        let abi = File::open(abi_path).expect("ABI not found.");
        let contract = ethabi::Contract::load(abi).unwrap();

        Bridge {
            wallet: verifier_wallet,
            password: password.to_owned(),
            contract: contract,
            main,
            side,
        }
    }

    pub fn start(&mut self) {
        // Create channels for communicating with main network
        let (from_main_tx, to_side_rx) = mpsc::channel::<Transfer>();
        self.main.set_tx(from_main_tx);

        // Create channels for communicating with side channel
        let (from_side_tx, to_main_rx) = mpsc::channel::<Transfer>();
        self.side.set_tx(from_side_tx);

        let abi = self.contract.clone();
        let wallet = self.wallet.clone();
        let password = self.password.clone();

        // main listen
        let mut main_listen = self.main.clone();
        let main = thread::spawn(move || {
            main_listen.listen();
        });

        // main withdraw
        let main_withdraw = self.main.clone();
        let withdraw_main = thread::spawn(move || {
            let mut iter = to_main_rx.iter();
            while let Some(transfer) = iter.next() {
                main_withdraw.withdraw(&abi, &wallet, &password, &transfer.tx_hash, &transfer.sender, *transfer.amount);
            }
        });

        // side listen
        let mut side_listen = self.side.clone();
        let side = thread::spawn(move || {
            side_listen.listen();
        });

        let abi = self.contract.clone();
        let wallet = self.wallet.clone();
        let password = self.password.clone();

        // side withdraw
        let side_withdraw = self.side.clone();
        let withdraw_side = thread::spawn(move || {
            let mut iter = to_side_rx.iter();
            while let Some(transfer) = iter.next() {
                side_withdraw.withdraw(&abi, &wallet, &password, &transfer.tx_hash, &transfer.sender, *transfer.amount);
            }
        });

        // No worries about a deadlock. None of these depend on one another.
        main.join().unwrap();
        side.join().unwrap();
        withdraw_side.join().unwrap();
        withdraw_main.join().unwrap();
    }

    pub fn stop(self) {
        self.main.cancel();
        self.side.cancel();
    }
}

#[derive(Clone)]
pub struct Network {
    name: String,
    web3: Web3<WebSocket>,
    contracts: Contracts,
    run: Arc<Mutex<bool>>,
    tx: Arc<Mutex<Option<mpsc::Sender<Transfer>>>>,
}

impl Network {
    pub fn new(name: &str, ws: WebSocket, token: &str, relay: &str) -> Network {
        let web3 = web3::Web3::new(ws);
        Network {
            name: name.to_string(),
            web3: web3,
            contracts: Contracts::new(token, relay),
            run: Arc::new(Mutex::new(false)),
            tx: Arc::new(Mutex::new(None)),
        }
    }

    pub fn cancel(self) {
        *self.run.lock().unwrap() = false;
        drop(self.web3);
        let mut lock = self.tx.lock().unwrap();
        if let Some(tx) = lock.clone() {
            drop(tx);
        }
        *lock = None;
    }

    pub fn set_tx(&mut self, sender: mpsc::Sender<Transfer>) {
        *self.tx.lock().unwrap() = Some(sender);
    }

    pub fn withdraw(&self, abi: &ethabi::Contract, wallet: &Address, password: &str, tx_hash: &H256, sender: &Address, value: U256) {
        println!("{}: Withdrawing {} to {:?}.", self.name.clone(), value, sender);
        let contract = Contract::new(self.web3.eth(), self.contracts.token_addr.clone(), abi.clone());
        self.web3.personal().unlock_account(wallet.clone(), password, Some(0xffff))
            .then(|_| {
                return contract.call("processWithdrawal", (tx_hash.clone(), sender.clone(), value), wallet.clone(), Options::default());
            })
            .wait()
            .unwrap();
    }

    pub fn listen(&mut self) {
        *self.run.lock().unwrap() = true;
        let contracts = &self.contracts;
        // Contractsall logs on the specified address
        let token = vec![contracts.token_addr];

        // Contractslogs on transfer topic
        let event_prototype = Contracts::generate_topic_filter();

        // Create filter on our subscription
        let fb: FilterBuilder = FilterBuilder::default()
            .address(token);

        // Start listening to events
        // Open Websocket and create RPC conn
        let mut sub = self.web3.eth_subscribe().subscribe_logs(fb.build()).wait().unwrap();

        println!("Got subscription id: {:?}", sub.id());

        let arc_run = self.run.clone();
        let arc_tx = self.tx.clone();
        (&mut sub)
        /*
         * Looks like at best, we can kill the subscription after it is cancelled
         * and geth receives an event. 
         */
            .take_while(|_x| {
                let run = arc_run.lock().unwrap().clone();
                Ok(run)
            })
            .for_each(|x| {
                /*
                 * Unfortunately, actually putting a topic filter on the
                 * subscribe_logs does not work.
                 */
                if x.topics[0] == event_prototype
                    && x.topics[2] == H256::from(&contracts.relay_addr) {
                    let Bytes(d) = x.data;
                    if let Some(tx) = arc_tx.lock().unwrap().clone() {
                        let amount = U256::from(&d[..]);
                        let from = Address::from(x.topics[1]);
                        let tx_hash = x.transaction_hash.unwrap();
                        let transfer = Transfer::new(&tx_hash, &from, &amount);
                        tx.send(transfer).unwrap();
                    }
                }
                Ok(())
            })
            .wait()
            .unwrap();
        sub.unsubscribe();
    }
}

///
/// # Contracts
///
/// This struct points to the relay & token contracts on the network. Use it
/// to generate the log filters (eventually)
///
#[derive(Debug, Clone)]
pub struct Contracts {
    // contract address to subscribe to
    token_addr: Address,
    // Relay contract address (Only care about deposits into that addr)
    relay_addr: Address,
}

impl Contracts{
    pub fn new(token: &str, relay: &str) -> Contracts {
        let mut start = match relay.starts_with("0x") {
            true => 2,
            false => 0
        };
        // Create an H160 address from address
        let token_hex: Address = token[start..40+start].parse().expect("Invalid token address.");

        start = match token.starts_with("0x") {
            true => 2,
            false => 0
        };
        let relay_hex: Address = relay[start..40+start].parse().expect("Invalid relay address.");

        Contracts{
            token_addr: token_hex,
            relay_addr: relay_hex,
        }
    }

    ///
    /// # Generate Topic Filter
    ///
    /// This generates the topics[0] filter for listening to a Transfer event. 
    /// Once filters work again, this will be a method and generate the whole
    /// (Option<Vec<H256>, Option<Vec<H256>, Option<Vec<H256>, Option<Vec<H256>)
    /// value.
    ///
    fn generate_topic_filter() -> Hash {
        // event Transfer(address indexed from, address indexed to, uint256 value)
        let from = EventParam {
            name: "from".to_string(),
            kind: ParamType::Address,
            indexed: true,
        };

        let to = EventParam {
            name: "to".to_string(),
            kind: ParamType::Address,
            indexed: true,
        };

        let value = EventParam {
            name: "value".to_string(),
            kind: ParamType::Uint(256),
            indexed: false,
        };

        let transfer_event = Event {
            name: "Transfer".to_string(),
            inputs: vec![from, to, value],
            anonymous: false,
        };
        transfer_event.signature()
    }
}

pub struct Transfer {
    pub tx_hash: Arc<H256>,
    pub sender: Arc<Address>,
    pub amount: Arc<U256>,
}

impl Transfer {
    pub fn new(tx_hash: &H256, sender: &Address, amount: &U256) -> Transfer {
        Transfer {
            tx_hash: Arc::new(tx_hash.clone()),
            sender: Arc::new(sender.clone()),
            amount: Arc::new(amount.clone()),
        }
    }
}