# Kelwyn

A lightweight, cross-platform shell interpreter written in Python.

```
██╗ ██╗████╗██╗   ██╗    ██╗██╗   ██╗███╗  ██╗
████╔╝ ██╗  ██║   ██║ █╗ ██║ ╚████╔╝ ██╔██╗██║
██║ ██╗████╗█████╗╚███╔███╔╝   ██║   ██║ ╚███║
╚═╝ ╚═╝╚═══╝╚════╝ ╚══╝╚══╝    ╚═╝   ╚═╝  ╚══╝  (v0.1.0)

Welcome to kelwyn shell - python-integrated command line interpreter
Type 'help' for available commands,'exit' to quit.

kelwyn ~/projects > _
```

## Core features

- **Smart interactive editing**: rich line editing with selection, clipboard copy, word-wise navigation, and fast in-line command correction.
- **Ghost suggestions from history**: live suggestions while typing, plus quick cycling and selection menus when typing commands.
- **Context-aware completion**: tab completion for paths, directories, and git branch/ref completion for common git commands.
- **Modular dynamic prompt**: Custom placeholders called **whippets** (`<cwd>`, `<git>`, `<hour>`, etc.) that automatically resolve in the prompt.
- **Template-style environment interpolation**: use `{{VARNAME}}` placeholders anywhere in a command before execution.
- **Inline expression and command evaluation**: use `eval(<python_expression>)` and `exec(<command>)` directly inside commands, with nested inner-first resolution.
- **Built-in command system with structured help**: command metadata, option parsing, examples, and `help` / `--help` support.
- **Comprehensive configuration**: External JSON-based configuration (`cfg/kelwyn-cfg.json`) to manage history/log paths, UI behavior, and detailed color schemes.
- **Advanced UI styling**: Support for HEX color codes and ANSI sequences for directory listings, git status (clean/dirty/conflict), and completion menus.
- **Extensible architecture**: easily add new commands, completers, and prompt whippets by dropping Python modules into designated folders.

---

## Requirements

- Python 3.10+
- Windows, macOS, or Linux
- No external dependencies (python standard libraries only)

---

## Starting Kelwyn

```bash
python src/kelwyn.py --run
python src/kelwyn.py --run --skip-init
python src/kelwyn.py --run --init-command "print hello"
python src/kelwyn.py --run --init-script path/to/init.kel
python src/kelwyn.py --run --history path/to/.kelwyn_history
python src/kelwyn.py --run --debug-log path/to/.kelwyn_debug.log
```

### CLI flags

- `--run`: start interactive shell mode
- `--skip-init`: skip default startup commands
- `--init-command CMD`: run one command at startup before prompt
- `--init-script PATH`: execute script file line by line at startup
- `--history PATH`: override history file location
- `--debug-log PATH`: override debug log location

### Notes

- If neither `--run` nor `--command` is provided, Kelwyn prints help and exits.
- `--command` is currently parsed by argparse but not executed as a one-shot command in this version.

---

## Init behavior

Startup order:

1. `--init-command` (if provided)
2. `--init-script` (if provided)
3. default startup commands (unless `--skip-init`):
   - `clear`
   - `banner`
   - `wellcome`

Init script rules:

- One command per line
- Empty lines are ignored
- Lines starting with `#` are ignored
- Inline `# comment` parsing is not supported

---

## Configuration

Kelwyn uses an external JSON configuration file at `cfg/kelwyn-cfg.json`. This file controls core behavior, interface sizes, and color schemes.

### Key Configuration Settings

- **File Paths**: `history_file` and `debug_log_file` locations.
- **System Prompt**: Template string using whippets (e.g., `"<month>/<day>·<hour><min><sec>"`).
- **Interface Limits**: Max history lines, debug log size, and UI component heights.
- **Color Customization**: Support for HEX codes (e.g., `"#FF5555"`) across all UI elements:
  - Error messages and ghost suggestions.
  - Selection colors (foreground/background).
  - Completion and Command Box styling.
  - Directory listing colors (`global_dir_color`, `global_file_color`).
  - Git status colors (`git_clean_color`, `git_dirty_color`, `git_conflict_color`).
  - Beta mode indicator (`beta_mode_color`).

---

## Command syntax

- Tokens are space-separated.
- Quoted strings use double quotes.
- To include `"` inside a quoted string, escape it by doubling (`""`).
- Built-in function tokens:
  - `eval(...)`
  - `exec(...)`

### Environment variable placeholders

- Syntax: `{{VARNAME}}`
- Expansion occurs before parsing and dispatch.
- Missing variables are left unchanged.

Examples:

```text
print {{USER}}
cd {{HOME}}
set ROOT C:/repos
print {{ROOT}}
```

---

## Built-in function calls

### eval(expression)

- Uses Python `eval()` with restricted globals:
  - `__builtins__` is empty
  - allowed modules: `math`, `cmath`, `random`
- Result is converted to string and injected as a quoted token.

```text
print eval(2+2)
print eval(math.sqrt(81))
```

### exec(command)

- Executes an inner Kelwyn command.
- Captures stdout/stderr and injects output as a quoted token.

```text
print exec(print 42)
print exec(print hello)
```

### Nesting and evaluation order

Kelwyn resolves calls from the most-inner outward in a loop:

1. Expand `{{VARNAME}}`
2. Find most-inner `eval(...)` or `exec(...)`
3. Replace with quoted result
4. Repeat until no built-in calls remain
5. Parse and execute final command

---

## Interactive features

### Prompt

Default prompt template includes date/time, current directory, and git status:

- git branch
- modified count (`:*`)
- behind count (`<<`)
- ahead count (`>>`)

Supported prompt placeholders (Whippets):

- `<year>`: 4-digit year
- `<month>`: month (`01`-`12`)
- `<day>`: day (`01`-`31`)
- `<hour>`: hour in 24h format (`00`-`23`)
- `<min>`: minute (`00`-`59`)
- `<sec>`: second (`00`-`59`)
- `<appname>`: application name (`kelwyn`)
- `<cwd>`: current working directory (absolute path)
- `<user>`: current OS username
- `<hostname>`: machine hostname
- `<git>`: git status segment for current directory (empty when not in a git repo)
- `<beta>`: `(beta)` marker when running from the `beta` folder (empty otherwise)
- `{%code%}`: ANSI escape sequence, where `code` is the sequence without the beginnig `\033[` prefix
- `{{VARNAME}}`: environment variable expansion. Missing variables replaced by VARNAME! string.

Example prompt template:

```text
{%94m%}[<year>-<month>-<day> <hour>:<min>:<sec>]{%0m%} <user>@<hostname> {%92m%}<cwd>{%0m%}<git> {%90m%}>{%0m%} 
```

### History

- History is loaded on startup and appended during session
- Consecutive duplicate entries are not stored
- Max in-memory history: 25000 commands

### Ghost suggestions

- At end of line, Kelwyn suggests suffix from recent history
- `Right`: accept suggestion
- `Alt+Up`: previous suggestion
- `Alt+Down`: next suggestion
- `Alt+Right`: open prefix-match selection menu
- `Ctrl+Alt+Right`: open pattern-match selection menu

### Tab completion

- Context-aware completion for:
  - file paths (fallback)
  - `cd` path argument (directories only)
  - many git commands (branch/ref completion)
- Multiple matches open an interactive option selector
- Values containing spaces are auto-quoted

### Editing and navigation keys

- `Up` / `Down`: history navigation
- `Left` / `Right`: move cursor
- `Ctrl+Left` / `Ctrl+Right`: move by word
- `Home` / `End`: jump start/end
- `Shift+Left` / `Shift+Right`: character selection
- `Ctrl+Shift+Left` / `Ctrl+Shift+Right`: word selection
- `Shift+Home` / `Shift+End`: select to start/end
- `Backspace` / `Delete`: delete text or selection
- `Ctrl+C`: copy selected text to clipboard (if selection exists)
- `Escape`: clear current input line
- `Enter`: execute command
- `Ctrl+D`: exit shell

---

## Command reference

### banner - Display the Kelwyn ASCII banner

Usage:

```text
banner
```

Options:

- none

### cd - Change current working directory

Usage:

```text
cd <path>
```

Options:

- `<path>` (required positional): destination directory path

### clear - Clear terminal screen

Usage:

```text
clear
```

Options:

- none

### get - Read an environment variable

Usage:

```text
get --name <name>
```

Options:

- `--name <name>`: variable name to read (required in practice)

### ls - List files and directories

Usage:

```text
ls [-r] [-h] [-f] [-v] [pattern]
```

Options:

- `-r`: recursive listing
- `-h`: include hidden entries (dot-prefix)
- `-f`: include inaccessible paths
- `-v`: vertical listing with file sizes
- `[pattern]` (optional positional): file pattern, supports `*` and `?`

Notes:

- Wildcards are only supported in the last path segment.

### print - Print text to console

By default, escape sequences are interpreted and a trailing newline is added.

Usage:

```text
print [--no-escape] [--no-newln] [text]
```

Options:

- `[text]` (optional positional): text to print
- `--no-escape`: do not interpret escape sequences
- `--no-newln`: do not append trailing newline

### set - Set an environment variable

Usage:

```text
set <name> <value>
```

Options:

- `<name>` (required positional): variable name
- `<value>` (required positional): variable value

### wellcome - Display welcome lines

Usage:

```text
wellcome
```

Options:

- none

### write - Write text to console

By default, escape sequences are not interpreted and no trailing newline is added.

Usage:

```text
write [--escape] [--newln] [text]
```

Options:

- `[text]` (optional positional): text to write
- `--escape`: interpret escape sequences
- `--newln`: append trailing newline

### help - Show command help

Usage:

```text
help
help <command>
<command> --help
```

Options:

- `<command>` (optional positional): command name
- `--help` (suffix form): show help for that command

### exit - Exit the shell

Usage:

```text
exit
```

Options:

- none

---

## External command execution

- Commands starting with `$` are executed by host shell directly.
- Unknown commands are also passed through to host shell.

Examples:

```text
$git status
python --version
```

---

## Extending Kelwyn

Kelwyn supports extension by dropping Python modules into three specialized folders:

- `src/commands`: adds new shell commands
- `src/completers`: adds new tab-completion strategies
- `src/whippets`: adds new dynamic prompt placeholders

Modules are loaded at startup automatically.

### Add a new command module

1. Create a new file in `src/commands`, for example `hello.py`.
2. Export `Get()` with command metadata (`name`, `description`, `options`, optional `examples`).
3. Export `Execute(Options)` that performs the command and returns `True` on success or `False` on error.

Minimal example:

```python
def Get():
  return {
    "name":"hello",
    "description":"Print hello message",
    "options":[
      {"type":"positional","name":"Name","index":1,"mandatory":False,"display":"<name>","description":"Optional name"}
    ],
    "examples":[
      {"command":"hello"},
      {"command":"hello John"}
    ]
  }

def Execute(Options):
  Name=Options.Name if Options.Name is not None else "world"
  print(f"Hello, {Name}!")
  return True
```

### Add a new completer module

1. Create a new file in `src/completers`, for example `hello_name.py`.
2. Export `Selector()` returning a list of selector entries.
3. Each selector entry contains:
   - `type`: unique selector id
   - `regex`: pattern matched against command text with active token replaced by `@token`
   - `completer`: function that returns options for the active token
4. Completer return format is a list of dicts: `{"text":..., "value":..., "color":...}`.

Minimal example:

```python
def Selector():
  return [
    {"type":"hello_name","regex":r"^hello\s+@token$","completer":CompleteHelloNames}
  ]

def CompleteHelloNames(Token):
  Names=["Diego","Kelwyn","World"]
  return [
    {"text":Name,"value":Name,"color":"#7F7F7F"}
    for Name in Names
    if Name.lower().startswith(Token.lower())
  ]
```

### Add a new whippet module

1. Create a new file in `src/whippets`, for example `hostname.py`.
2. Export `Whippet(Config)` receiving the shell configuration as a dictionary.
3. The function must return a string which will replace the placeholder `<filename>` in the prompt template.

Minimal example:

```python
import socket

def Whippet(Config):
  # Return the machine hostname
  return socket.gethostname()
```

### Extension tips

- Keep option names stable: parsed options are exposed as attributes in `Options`.
- Use command metadata examples: they automatically appear in `help <command>`.
- Handle exceptions inside `Execute` and return `False` on failure.
- If multiple completers match, selector order can affect which one is used first.

---

## License

See [LICENSE](LICENSE).
