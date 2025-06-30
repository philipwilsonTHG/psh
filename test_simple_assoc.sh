#!/opt/homebrew/bin/bash
declare -A colors=([red]="#FF0000" [green]="#00FF00" [blue]="#0000FF")
echo "All keys: ${!colors[@]}"