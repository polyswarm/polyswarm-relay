#!/usr/bin/env ruby

ROOTDIR     = "/usr/src/app"
TRUFFLE_DIR = "#{ROOTDIR}/truffle"

#
# XXX these update .cfg files should be
#     properly located if required by
#     polyswarm/polyswarmd container.
#     since polyswarm/queenb, this container
#     mounts to specific volume and referred
#     by the caller, polyswarmd.
#
DOCKER_CONFIG = "#{TRUFFLE_DIR}/polyswarmd.docker.cfg"
CONFIG        = "#{TRUFFLE_DIR}/polyswarmd.cfg"

def say(txt)
  puts "[#{txt}] ..."
end

def say_and_do(txt)
  puts "[#{txt}] ..."
  system txt
end

def dev_null(cmd)
  say "#{cmd} >/dev/null &"
  system "#{cmd} >/dev/null &"
end

def migrate
  say "migration start ..."
  response = `cd #{TRUFFLE_DIR}; sudo truffle migrate --reset`
  puts   response
  return response
end

def parse_response_into_token(response)
  nectar_token    = /NectarToken\:.+/.match(response).to_s.gsub("NectarToken: ", "")
  bounty_registry = /BountyRegistry\:.+/.match(response).to_s.gsub("BountyRegistry: ", "")
  config = "NECTAR_TOKEN_ADDRESS    = '#{nectar_token}'\n" + 
           "BOUNTY_REGISTRY_ADDRESS = '#{bounty_registry}'"

  return config
end

sleep 3

#
# MIGRATE AND GENERATE THE CONFIG FILE
# 
say ">> sudo truffle migrate --reset"
config = parse_response_into_token(migrate)

File.open(DOCKER_CONFIG, "w") { |f| f.puts config }
File.open(CONFIG, "w") { |f| f.puts config }

say    "truffle reset done"

say    DOCKER_CONFIG
system "cat #{DOCKER_CONFIG}"

say    CONFIG
system "cat #{CONFIG}"
