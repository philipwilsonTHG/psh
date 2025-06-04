factorial() {
    local n=$1
    
    # Base case: 0! = 1, 1! = 1  
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    
    # For small values, do direct calculation to avoid deep recursion
    if [ "$n" -eq 2 ]; then
        echo 2
        return
    fi
    
    if [ "$n" -eq 3 ]; then
        echo 6
        return
    fi
    
    if [ "$n" -eq 4 ]; then
        echo 24
        return
    fi
    
    if [ "$n" -eq 5 ]; then
        echo 120
        return
    fi
    
    # For larger values, use iterative approach
    local result=1
    local i=1
    
    while [ "$i" -le "$n" ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    
    echo $result
}
