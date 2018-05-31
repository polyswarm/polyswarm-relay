if [[ $OS =~ ^Ubuntu ]]; then 
  sudo apt-get install ruby-dev -y
fi

sudo gem install websocket-eventmachine-client
sudo gem install websocket
sudo gem install rspec
sudo gem install rspec-support
sudo gem install rspec-core
sudo gem install rest-client
sudo gem install pry
sudo gem install netrc
sudo gem install os
sudo gem install mocha
sudo gem install mime-types
sudo gem install mime-types-data
sudo gem install method_source
sudo gem install metaclass -v "=0.0.4"
sudo gem install http-cookie -v "=1.0.3"
sudo gem install domain_name -v "=0.5.20170404"
sudo gem install unf_ext
sudo gem install coderay
sudo gem install diff-lcs
sudo gem install unf
sudo gem install bundle
bundle install

function test {
  sudo $HOME/.queenb/util/tmp/polyswarmd/truffle/scripts/mint_tokens.sh
  rspec spec/integration/micro_engine_spec.rb
}
scripts/kill_tcp_zombee.sh
test
