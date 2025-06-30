#!/opt/homebrew/bin/bash
declare -A test=([red]="#FF0000" [green]="#00FF00" [blue]="#0000FF")
echo "Keys: ${!test[@]}"
echo "Values: ${test[@]}"