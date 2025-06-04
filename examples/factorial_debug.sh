#!/usr/bin/env psh
# Debug version of factorial

# Simple factorial function
factorial() {
    if [ $1 -le 1 ]; then
        echo 1
    else
        n=$1
        result=1
        i=2
        while [ $i -le $n ]; do
            result=$((result * i))
            i=$((i + 1))
        done
        echo $result
    fi
}

echo "Testing factorial function..."

# Test directly first
echo "Direct calls:"
echo "factorial 1 = $(factorial 1)"
echo "factorial 5 = $(factorial 5)"
echo "factorial 10 = $(factorial 10)"

echo ""
echo "Testing in a for loop:"
for n in 1 5 10; do
    echo -n "factorial $n = "
    factorial $n
done