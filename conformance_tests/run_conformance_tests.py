#!/usr/bin/env python3
import argparse
import glob
import subprocess
import os
import difflib
import sys
import signal
import shutil

# Handle SIGPIPE gracefully for piping to less, head, etc.
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_shell(shell_name):
    """Find the best available shell executable.

    Searches for the shell in the following order:
    1. Environment variable (BASH_PATH for bash, DASH_PATH for dash)
    2. Homebrew locations (/opt/homebrew/bin, /usr/local/bin)
    3. Standard locations (/bin, /usr/bin)
    4. Shell in PATH

    Args:
        shell_name: Name of the shell (e.g., 'bash', 'dash')

    Returns:
        Path to shell executable

    Raises:
        FileNotFoundError: If shell cannot be found
    """
    # Check environment variable
    env_var = f"{shell_name.upper()}_PATH"
    if env_var in os.environ:
        shell_path = os.environ[env_var]
        if os.path.isfile(shell_path) and os.access(shell_path, os.X_OK):
            return shell_path

    # Check common locations (Homebrew first, then standard)
    search_paths = [
        f"/opt/homebrew/bin/{shell_name}",  # Apple Silicon Homebrew
        f"/usr/local/bin/{shell_name}",      # Intel Mac Homebrew
        f"/bin/{shell_name}",                # Standard location
        f"/usr/bin/{shell_name}",            # Alternative standard location
    ]

    for path in search_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Fall back to shell in PATH
    shell_in_path = shutil.which(shell_name)
    if shell_in_path:
        return shell_in_path

    raise FileNotFoundError(f"Could not find {shell_name} executable")

def run_test(test_input_path, mode, update_golden=False, compare_shell=None):
    golden_file = os.path.splitext(test_input_path)[0] + ".golden"
    with open(test_input_path, "r") as f:
        input_data = f.read()

    # Run PSH test
    env = os.environ.copy()
    env["PSH_MODE"] = mode
    # Clear OLDPWD to avoid inheriting previous directory changes
    env.pop("OLDPWD", None)
    # Ensure we use the local development version of PSH
    psh_root = os.path.dirname(SCRIPT_DIR)
    env["PYTHONPATH"] = psh_root
    cmd = ["python3", "-m", "psh"]
    try:
        proc = subprocess.run(cmd, input=input_data, text=True, capture_output=True, check=True, env=env, cwd=os.getcwd())
        psh_output = proc.stdout
    except subprocess.CalledProcessError as e:
        psh_output = e.stdout + e.stderr

    normalized_psh_output = normalize(psh_output)
    
    # If comparing with another shell, run that too
    if compare_shell:
        try:
            compare_proc = subprocess.run([compare_shell], input=input_data, text=True, capture_output=True, check=True, env=env, cwd=os.getcwd())
            compare_output = compare_proc.stdout
        except subprocess.CalledProcessError as e:
            compare_output = e.stdout + e.stderr
        except FileNotFoundError:
            return False, f"Comparison shell '{compare_shell}' not found"
        
        normalized_compare_output = normalize(compare_output)
        
        if normalized_psh_output != normalized_compare_output:
            diff = "".join(difflib.unified_diff(
                normalized_compare_output.splitlines(keepends=True),
                normalized_psh_output.splitlines(keepends=True),
                fromfile=f"{compare_shell} output",
                tofile="psh output"
            ))
            return False, f"PSH output differs from {compare_shell}:\n{diff}"
        return True, None

    # Normal golden file comparison
    if update_golden:
        with open(golden_file, "w") as f:
            f.write(normalized_psh_output)
        return True, None

    if not os.path.exists(golden_file):
        return False, "Golden file does not exist: " + golden_file

    with open(golden_file, "r") as f:
        golden = f.read()
    normalized_golden = normalize(golden)

    if normalized_psh_output != normalized_golden:
        diff = "".join(difflib.unified_diff(
            normalized_golden.splitlines(keepends=True),
            normalized_psh_output.splitlines(keepends=True),
            fromfile="golden",
            tofile="current"
        ))
        return False, diff
    return True, None

def normalize(text: str) -> str:
    # Normalize by stripping trailing whitespace from each line and ensuring a final newline
    return "\n".join(line.rstrip() for line in text.strip().splitlines()) + "\n"

def discover_tests(test_dir, category=None):
    """Recursively discover test files, optionally filtered by category."""
    test_files = []
    
    if category:
        # Look in specific category subdirectory
        category_dir = os.path.join(test_dir, category)
        if os.path.exists(category_dir):
            test_files.extend(glob.glob(os.path.join(category_dir, "*.input")))
        else:
            print(f"Warning: Category directory {category_dir} does not exist.")
    else:
        # Recursively find all .input files
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith(".input"):
                    test_files.append(os.path.join(root, file))
    
    return sorted(test_files)

def run_tests_in_dir(test_dir, mode, category=None, update_golden=False, compare_shell=None):
    test_files = discover_tests(test_dir, category)
    failures = {}
    passed = 0
    
    for test in test_files:
        success, diff = run_test(test, mode, update_golden, compare_shell)
        if not success:
            failures[test] = diff
        else:
            passed += 1
    
    return failures, passed

def main():
    parser = argparse.ArgumentParser(description="Run conformance tests for PSH via golden files")
    parser.add_argument("--update-golden", action="store_true", help="Update golden files with current output")
    parser.add_argument("--mode", choices=["posix", "bash", "all"], default="all", help="Conformance mode to test (default: all)")
    parser.add_argument("--category", help="Run tests in specific category (e.g., builtins, expansions, arithmetic)")
    parser.add_argument("--list-categories", action="store_true", help="List available test categories")
    parser.add_argument("--compare-shell", help="Compare PSH output with another shell (e.g., /opt/homebrew/bin/dash)")
    parser.add_argument("--dash-compare", action="store_true", help="Compare PSH output with dash POSIX shell")
    parser.add_argument("--bash-compare", action="store_true", help="Compare PSH output with bash shell")
    args = parser.parse_args()

    # List categories if requested
    if args.list_categories:
        posix_dir = "posix"
        if os.path.exists(posix_dir):
            categories = [d for d in os.listdir(posix_dir) if os.path.isdir(os.path.join(posix_dir, d))]
            print("Available categories:")
            for cat in sorted(categories):
                print(f"  {cat}")
        else:
            print("No conformance tests directory found.")
        sys.exit(0)

    # Handle comparison shell options
    compare_shell = None
    if args.dash_compare:
        try:
            compare_shell = find_shell("dash")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.bash_compare:
        try:
            compare_shell = find_shell("bash")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.compare_shell:
        compare_shell = args.compare_shell

    failures = {}
    total_passed = 0
    base_dirs = []
    
    if args.mode == "all":
        base_dirs = [("posix", "posix"), ("bash", "bash")]
    else:
        base_dirs = [(args.mode, args.mode)]

    for mode, directory in base_dirs:
        # Use absolute path relative to script directory
        abs_directory = os.path.join(SCRIPT_DIR, directory)
        if not os.path.exists(abs_directory):
            print(f"Warning: Directory {directory} does not exist. Skipping.")
            continue
        
        mode_failures, mode_passed = run_tests_in_dir(abs_directory, mode, args.category, args.update_golden, compare_shell)
        failures.update(mode_failures)
        total_passed += mode_passed
        
        if compare_shell:
            shell_name = os.path.basename(compare_shell)
            if args.category:
                print(f"Category '{args.category}' in {mode} mode (vs {shell_name}): {mode_passed} passed, {len(mode_failures)} failed")
            else:
                print(f"{mode.upper()} mode (vs {shell_name}): {mode_passed} passed, {len(mode_failures)} failed")
        else:
            if args.category:
                print(f"Category '{args.category}' in {mode} mode: {mode_passed} passed, {len(mode_failures)} failed")
            else:
                print(f"{mode.upper()} mode: {mode_passed} passed, {len(mode_failures)} failed")

    if args.update_golden:
        print(f"Golden files updated for {total_passed} tests.")
        sys.exit(0)

    if failures:
        print(f"\nSome tests failed ({len(failures)} total):")
        for test, diff in failures.items():
            print(f"\nTest {test} failed:")
            print(diff)
        sys.exit(1)
    else:
        print(f"\nAll conformance tests passed! ({total_passed} tests)")
        sys.exit(0)

if __name__ == "__main__":
    main()