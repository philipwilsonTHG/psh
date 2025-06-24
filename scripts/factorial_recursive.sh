factorial() {
    n=$1
    
    # Base case
    if [ $n -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Recursive case: n * factorial(n-1)
    prev=$((n - 1))
    prev_factorial=$(factorial $prev)
    echo $((n * prev_factorial))
}
