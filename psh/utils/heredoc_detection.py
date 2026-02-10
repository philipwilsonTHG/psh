"""Heredoc detection heuristic for distinguishing << heredocs from << bit-shift."""


def contains_heredoc(command_string: str) -> bool:
    """Check if command contains heredoc operators (not bit-shift in arithmetic).

    Returns True if the command contains << that's likely a heredoc,
    False if << only appears inside arithmetic expressions.
    """
    if '<<' not in command_string:
        return False

    # Quick check: if we have arithmetic expressions, check if << is inside them
    # This is a simple heuristic that handles the common case
    if '((' in command_string:
        # Find all arithmetic expression boundaries
        arith_start = []
        arith_end = []
        i = 0
        while i < len(command_string) - 1:
            if command_string[i:i+2] == '((':
                arith_start.append(i)
                i += 2
            elif command_string[i:i+2] == '))':
                arith_end.append(i + 2)
                i += 2
            else:
                i += 1

        # Find all << positions
        heredoc_positions = []
        i = 0
        while i < len(command_string) - 1:
            if command_string[i:i+2] == '<<':
                heredoc_positions.append(i)
                i += 2
            else:
                i += 1

        # Check if all << are inside arithmetic expressions
        if heredoc_positions and arith_start and arith_end:
            all_inside_arithmetic = True
            for pos in heredoc_positions:
                inside = False
                # Check if this << is inside any arithmetic expression
                for j in range(min(len(arith_start), len(arith_end))):
                    if arith_start[j] < pos < arith_end[j]:
                        inside = True
                        break
                if not inside:
                    all_inside_arithmetic = False
                    break

            # If all << are inside arithmetic expressions, no heredoc
            if all_inside_arithmetic:
                return False

    # Default: assume << is a heredoc
    return True
