#!/usr/bin/env ruby

puts "prune..."
system "sudo docker system prune --force"

containers = `sudo docker ps -a`
               .split("\n")
               .map{|l| /[\da-z]+/.match(l) }
               .compact

containers.each do |container|
  puts "stop #{container}..."
  system "sudo docker stop #{container}"
end

puts "removing stuff..."
system "sudo docker rm -f $(sudo docker ps -aq)"
