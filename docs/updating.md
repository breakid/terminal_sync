# Updating terminal_sync

1. Use `git pull` to get the latest updates or download an updated zip archive from GitHub
2. Update the server
    - If using Docker, run `docker-compose up -d --build` to rebuild the image
    - If using Python, run `pdm install --prod` to install any new or updated packages
3. Update any installed terminal hooks
    1. Overwrite the previous script / module file with the updated version (if the `git pull` didn't do this automatically); be sure to update the new script / module with any configuration changes you made to the old one
    2. Start a new shell session
