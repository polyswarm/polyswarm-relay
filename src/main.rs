extern crate clap;
extern crate ctrlc;
extern crate ethabi;
#[macro_use]
extern crate serde_derive;
extern crate toml;
extern crate web3;

use clap::{App, Arg};

mod relay;
mod config;

fn main() {
    let matches = App::new("Polyswarm Relay Bridge.")
        .version("0.0.1")
        .author("Polyswarm Developers <info@polyswarm.io>")
        .about("Bridges between two contracts on different networks.")
        .arg(
            Arg::with_name("config")
                .value_name("TOML configuration file")
                .help("Configures the two networks we will bridge")
                .required(true)
                .takes_value(true),
        )
        .get_matches();

    let config_file = matches
        .value_of("config")
        .expect("You must pass a config file.");
    let configuration = config::read_config(config_file);

    let abi = configuration.bridge.path;
    let wallet = configuration.bridge.wallet;
    // I don't plan on having the password in the config for long. Will prompt.
    let password = configuration.bridge.password;

    let main = configuration.bridge.main;
    let side = configuration.bridge.side;

    // Stand up the networks in the bridge
    let (_main_eloop, main_ws) = web3::transports::WebSocket::new(&main.host).unwrap();

    let private = relay::Network::new(&main.name, main_ws.clone(), &main.token, &main.relay);

    let (_side_eloop, side_ws) = web3::transports::WebSocket::new(&side.host).unwrap();
    let poa = relay::Network::new(&side.name, side_ws.clone(), &side.token, &side.relay);

    // Create the bridge
    let mut bridge = relay::Bridge::new(&wallet, &password, &abi, private.clone(), poa.clone());

    // Kill the bridge & close subscriptions on Ctrl-C
    // let b = bridge.clone();
    // ctrlc::set_handler(move || {
    //     println!("\rExiting...");
    //     let mut a = b.clone();
    //     a.stop();
    // }).expect("Unable to setup Ctrl-C handler.");

    // Start relay.
    bridge.start();
}
