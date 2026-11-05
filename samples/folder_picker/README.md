# Loopback-only folder picker

When you choose a project folder, Aria shows a folder browser in the browser window. Because that browser window can reach Aria's local web interface, so could any other website open in the same browser. This sample shows how the folder listing is protected against that.

## What it demonstrates

- **Folders only.** Given a directory, the listing returns the names and paths of the folders inside it, plus the parent folder. It never returns file names or file contents, and it skips entries it is not allowed to read.
- **Loopback only.** A request is answered only when three things all point to the computer Aria runs on: the address the request came from, the `Host` header, and the `Origin` header if the browser sent one.
- **Protection from other websites.** Checking `Host` defeats DNS rebinding, where a malicious site makes its own domain name point at your computer. Checking `Origin` blocks a request that another website's page tries to send to Aria in the background.
- **Cross-platform starting point.** The first view is your home folder, with shortcuts to every drive letter on Windows, or to the filesystem root on macOS.

## Run the test

```
python test_folder_picker.py
```

The test builds a temporary directory with folders and a file, and confirms that only the folders are listed, that the file's name and contents never appear, that unreadable entries are skipped, and that missing paths and file paths are rejected. It also checks the loopback rules against spoofed addresses, foreign `Host` headers, and foreign or `null` origins.

Requires Python 3.11 or later. No third-party packages.
