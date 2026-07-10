# VHS tape — record the Synapse demo GIF for the README.
# Requires: https://github.com/charmbracelet/vhs  (`brew install vhs`)
# Usage:  vhs docs/demo.tape
# Output: docs/assets/synapse-demo.gif
Output docs/assets/synapse-demo.gif
Set FontSize 16
Set Width 980
Set Height 560
Set Theme "Catppuccin Mocha"
Set PlaybackSpeed 1
Set TypingSpeed 40ms

Hide
Type "cd $(git rev-parse --show-toplevel) && clear"
Enter
Show

Type "# Synapse — learn → write → recall (plain Markdown, no DB)"
Enter
Sleep 1s
Type "bash scripts/demo.sh"
Enter
Sleep 8s
Type "# That's it — your agent memory is just files you own."
Enter
Sleep 2s
