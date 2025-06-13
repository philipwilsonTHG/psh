# Key Bindings in PSH

PSH supports both Emacs and Vi key bindings for command line editing. The default mode is Emacs.

## Setting the Edit Mode

```bash
# Set vi mode
set -o vi

# Set emacs mode (default)
set -o emacs

# Show current mode
set -o

# Disable vi mode (returns to emacs)
set +o vi
```

## Emacs Key Bindings

### Movement
- `Ctrl-A`: Move to beginning of line
- `Ctrl-E`: Move to end of line
- `Ctrl-F`: Move forward one character
- `Ctrl-B`: Move backward one character
- `Alt-F`: Move forward one word
- `Alt-B`: Move backward one word

### Editing
- `Ctrl-D`: Delete character under cursor (or EOF on empty line)
- `Ctrl-H` or `Backspace`: Delete character before cursor
- `Ctrl-K`: Kill (cut) from cursor to end of line
- `Ctrl-U`: Kill entire line
- `Ctrl-W`: Kill word backward
- `Alt-D`: Kill word forward
- `Ctrl-Y`: Yank (paste) from kill ring
- `Ctrl-T`: Transpose characters

### History
- `Ctrl-P` or `Up Arrow`: Previous command
- `Ctrl-N` or `Down Arrow`: Next command
- `Ctrl-R`: Reverse search history
- `Alt-<`: Move to first history entry
- `Alt->`: Move to last history entry

### Other
- `Ctrl-L`: Clear screen
- `Ctrl-C`: Cancel current line
- `Tab`: Complete filename

## Vi Key Bindings

### Mode Switching
- `ESC`: Enter normal mode from insert mode
- `i`: Enter insert mode before cursor
- `I`: Enter insert mode at beginning of line
- `a`: Enter insert mode after cursor
- `A`: Enter insert mode at end of line

### Normal Mode Movement
- `h`: Move left
- `l`: Move right
- `j`: Next command in history
- `k`: Previous command in history
- `w`: Move forward one word
- `b`: Move backward one word
- `0`: Move to beginning of line
- `$`: Move to end of line

### Normal Mode Editing
- `x`: Delete character under cursor
- `X`: Delete character before cursor
- `dd`: Delete entire line
- `D`: Delete from cursor to end of line
- `dw`: Delete word forward
- `db`: Delete word backward
- `cw`: Change word
- `cc`: Change entire line
- `r`: Replace single character

### Insert Mode
- All normal typing works
- `Ctrl-W`: Delete word backward
- `Ctrl-U`: Delete to beginning of line
- `Tab`: Complete filename

## History Search

In both Emacs and Vi modes, you can search through command history:

1. Press `Ctrl-R` to start reverse search
2. Type characters to search for
3. Press `Ctrl-R` again to find next match
4. Press `Ctrl-S` to search forward
5. Press `Enter` to execute the found command
6. Press `Ctrl-G` or `ESC` to cancel search

## Implementation Notes

- The kill ring stores deleted/cut text for yanking
- Vi mode starts in insert mode for each new command
- History search works incrementally as you type
- Tab completion works the same in both modes