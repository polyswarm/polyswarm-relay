use config::{Config, Environment, File};
use std::path::Path;

use super::errors::*;

/// Settings for the application
#[derive(Debug, Deserialize)]
pub struct Settings {
    /// Relay settings
    pub relay: Relay,
}

/// Relay settings
#[derive(Debug, Deserialize)]
pub struct Relay {
    /// The account to send transactions from
    pub account: String,
    /// The password to unlock the account
    pub password: String,
    /// Number of blocks to wait for confirmation
    pub confirmations: u64,
    /// Frequency of sidechain anchor blocks
    pub anchor_frequency: u64,
    /// Network to use as the homechain
    pub homechain: Network,
    /// Network to use as the sidechain
    pub sidechain: Network,
}

/// Per-network settings
#[derive(Debug, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct Network {
    /// URI for the Websocket RPC endpoint for an Ethereum client
    pub ws_uri: String,
    /// Address of the ERC20 token contract to use
    pub token: String,
    /// Address of the ERC20Relay contract to use
    pub relay: String,
}

impl Settings {
    /// Construct a new settings object from a file path and the environment
    ///
    /// # Arguments
    ///
    /// * `path` - Path to a configuration file
    pub fn new<P>(path: Option<P>) -> Result<Self>
    where
        P: AsRef<Path>,
    {
        let mut c = Config::new();

        c.set_default("relay.confirmations", 12)?;
        c.set_default("relay.anchor_frequency", 100)?;

        if let Some(p) = path {
            let ps = p.as_ref().to_str().chain_err(|| ErrorKind::InvalidConfigFilePath)?;
            c.merge(File::with_name(ps))?;
        }

        c.merge(Environment::new())?;
        c.try_into().map_err(|e| e.into()).and_then(|s: Self| s.validated())
    }

    fn validated(self) -> Result<Self> {
        if self.relay.anchor_frequency == 0 {
            Err(ErrorKind::InvalidAnchorFrequency.into())
        } else if self.relay.confirmations >= self.relay.anchor_frequency {
            Err(ErrorKind::InvalidConfirmations.into())
        } else {
            Ok(self)
        }
    }
}
