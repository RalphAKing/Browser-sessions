# Browser Sessions Manager

A powerful tool to manage multiple Chrome browser sessions with automatic tab pinning and credential auto-fill capabilities.

## Features

- Create and manage multiple browser sessions
- Automatically pin specified tabs for each session
- Auto-fill credentials for configured websites
- Web-based UI for easy management
- Command-line interface support
- Fresh session launch option

## Usage

### Web Interface

Start the web interface with:

```bash
python browsersessions.py --webui
```

Access the interface at `http://localhost:5000`

### Command Line

Launch a specific session:

```bash
python browsersessions.py --session work
```

Launch a fresh session (clearing existing profile):

```bash
python browsersessions.py --session work --fresh
```

## Configuration

The application stores all configurations in an SQLite database (`sessions.db`). Through the web interface, you can:

- Create new sessions
- Add pinned tabs to sessions
- Configure website credentials
- Manage existing sessions

## Requirements

- Python 3.6+
- Google Chrome installed
- Flask
- SQLite3

## Security Note

Credentials are stored in a local SQLite database. While convenient, please be aware of the security implications of storing sensitive information.

## How It Works

1. **Session Management**: Each session maintains its own Chrome profile directory
2. **Auto-Pin Extension**: Automatically pins specified tabs using a custom Chrome extension
3. **Auto-Fill Extension**: Automatically fills credentials on configured websites
4. **Profile Isolation**: Each session runs in an isolated Chrome profile for security

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open-source and available for modification and use under the MIT license.

### MIT License

```
MIT License

Copyright (c) 2025 Ralph King

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## Author

Ralph King
