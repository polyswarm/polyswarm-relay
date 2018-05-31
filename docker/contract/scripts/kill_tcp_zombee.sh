#!/usr/bin/env ruby

procs = `lsof -i 4tcp:31337 -sTCP:LISTEN | grep ruby`.split("\n").map{|p| p.split(" ")[1]}.select{|p| /\d+/ =~ p}
procs.each do |p|
  puts "kill #{p}"
  system "kill #{p}"
end
