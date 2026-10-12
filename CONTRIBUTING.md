# Contributing

Bug reports, ideas, and pull requests are welcome.

## Reporting an issue

Include the command you ran, what you expected to happen, and the error output. Do not include
private URLs, credentials, or other sensitive information.

## Making a change

1. Create a branch for your change.
2. Keep changes focused and update the README when user-facing behavior changes.
3. Build the Docker image and check the CLI:

   ```bash
   docker build -t pyclip .
   docker run --rm pyclip --help
   ```

4. Describe the change and the checks you ran in your pull request.

The project currently has no automated test suite. Avoid relying on a live YouTube download as
a routine check; it requires network access and depends on the remote video being available.
