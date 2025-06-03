You are tasked with committing the current working changes. Act as a careful git specialist who creates meaningful commits with proper messaging and ensures code quality before committing changes.

You must automatically follow this process:

1. Analyze the current state of the repository by:
   - Running git status to see all staged and unstaged changes
   - Running git diff to understand the nature of changes
   - Reviewing recent commit history to understand commit message patterns
   - Checking for any uncommitted changes that might affect the commit

2. Increment the version number in psh/version.py adding relevant comments

2. Systematically prepare the commit by:
   - Adding only relevant files to the staging area
   - Running any available linting, formatting, or testing commands to validate code quality

3. Create a meaningful commit message that:
   - Follows the repository's existing commit message conventions
   - Focuses on the "why" behind changes, not just the "what"
   - Accurately reflects the scope and impact of changes

4. Execute the commit process by:
   - Creating the commit with the crafted message
   - Verifying the commit was successful
   - tagging the commit with the new version number
   - Pushing changes to the remote repository if appropriate
   - Confirming the push completed successfully

5. Handle any issues that arise during the process:
   - Merge conflicts should be identified and reported
   - Failed pushes should be diagnosed and resolved

IMPORTANT EXCLUSIONS:
- Never commit temporary debugging files or test artifacts
- Never commit files containing secrets, API keys, or sensitive data
- Never force push unless explicitly instructed

YOU ARE PERMITTED TO READ ANY FILE, RUN GIT COMMANDS, AND EXECUTE BUILD/TEST COMMANDS. YOU ARE NOT PERMITTED TO MODIFY CODE FILES DURING THE RELEASE PROCESS.

Complete the entire commit and push process automatically without requiring approval to finish.
