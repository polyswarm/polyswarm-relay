ARTIFACT=$1
curl -s -F file=@$ARTIFACT http://localhost:31337/artifacts
