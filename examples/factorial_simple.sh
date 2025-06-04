# Simple factorial function for psh
factorial() {
    if [ $1 -eq 0 ] || [ $1 -eq 1 ]; then
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

# Example usage:
# factorial 5   # outputs: 120
# factorial 10  # outputs: 3628800