# ---------------------------------------------------------------------------------------------------------------------
# ansi.py: ANSI escape sequences
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import os
import re

# ---------------------------------------------------------------------------------------------------------------------
# Escape sequences for colors screen and and cursor control
# ---------------------------------------------------------------------------------------------------------------------
_ESCAPE_PREFIX    ="\033["
_CLEAR_SCREEN     =_ESCAPE_PREFIX+"2J"
_CURSOR_GO_HOME   =_ESCAPE_PREFIX+"H"
_CURSOR_SET_POS   =_ESCAPE_PREFIX+"{row};{col}H"
_CURSOR_MOVE_LEFT =_ESCAPE_PREFIX+"{n}D"
_CURSOR_MOVE_RIGHT=_ESCAPE_PREFIX+"{n}C"
_CURSOR_MOVE_UP   =_ESCAPE_PREFIX+"{n}A"
_CURSOR_MOVE_DOWN =_ESCAPE_PREFIX+"{n}B"
_RESET_COLOR      =_ESCAPE_PREFIX+"0m"
_SCROLL_UP        =_ESCAPE_PREFIX+"{n}S"
_SCROLL_DOWN      =_ESCAPE_PREFIX+"{n}T"
_QUERY_CURSOR_POS =_ESCAPE_PREFIX+"6n"
_ENTER_ALT_SCREEN =_ESCAPE_PREFIX+"?1049h"
_EXIT_ALT_SCREEN  =_ESCAPE_PREFIX+"?1049l"
_HIDE_CURSOR      =_ESCAPE_PREFIX+"?25l"
_SHOW_CURSOR      =_ESCAPE_PREFIX+"?25h"

# ---------------------------------------------------------------------------------------------------------------------
# ANSI color codes
# ---------------------------------------------------------------------------------------------------------------------
ANSI_COLORS={
  "dark_black"    :{"foreground":30,"background":40 }, ##000000
  "dark_red"      :{"foreground":31,"background":41 }, ##7F0000
  "dark_green"    :{"foreground":32,"background":42 }, ##007F00
  "dark_yellow"   :{"foreground":33,"background":43 }, ##7F7F00
  "dark_blue"     :{"foreground":34,"background":44 }, ##00007F
  "dark_magenta"  :{"foreground":35,"background":45 }, ##7F007F
  "dark_cyan"     :{"foreground":36,"background":46 }, ##007F7F
  "dark_white"    :{"foreground":37,"background":47 }, ##7F7F7F
  "bright_black"  :{"foreground":90,"background":100}, ##7F7F7F
  "bright_red"    :{"foreground":91,"background":101}, ##FF0000
  "bright_green"  :{"foreground":92,"background":102}, ##00FF00
  "bright_yellow" :{"foreground":93,"background":103}, ##FFFF00
  "bright_blue"   :{"foreground":94,"background":104}, ##0000FF
  "bright_magenta":{"foreground":95,"background":105}, ##FF00FF
  "bright_cyan"   :{"foreground":96,"background":106}, ##00FFFF
  "bright_white"  :{"foreground":97,"background":107}, ##FFFFFF
}

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to set foreground color
# Args:
# - Color (string): Foreground color code (from ANSI_COLORS), or HEX value in format #RRGGBB
# Returns:
# - string: ANSI escape sequence for the specified color
# ---------------------------------------------------------------------------------------------------------------------
def SetFgColor(Color):
  if Color in ANSI_COLORS:
    return f"{_ESCAPE_PREFIX}{ANSI_COLORS[Color]["foreground"]}m"
  elif re.match(r'^#[0-9a-fA-F]{6}$',Color):
    RedColorDecimal=int(Color[1:3],16)
    GreenColorDecimal=int(Color[3:5],16)
    BlueColorDecimal=int(Color[5:7],16)
    RgbColor=f"{RedColorDecimal};{GreenColorDecimal};{BlueColorDecimal}"
    return f"{_ESCAPE_PREFIX}38;2;{RgbColor}m"
  else:
    raise ValueError(f"Invalid color specification ({Color})")
  return None

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to set foreground color
# Args:
# - Color (string): Foreground color code (from ANSI_COLORS), or HEX value in format #RRGGBB
# Returns:
# - string: ANSI escape sequence for the specified color
# ---------------------------------------------------------------------------------------------------------------------
def SetBkColor(Color):
  if Color in ANSI_COLORS:
    return f"{_ESCAPE_PREFIX}{ANSI_COLORS[Color]["background"]}m"
  elif re.match(r'^#[0-9a-fA-F]{6}$',Color):
    RedColorDecimal=int(Color[1:3],16)
    GreenColorDecimal=int(Color[3:5],16)
    BlueColorDecimal=int(Color[5:7],16)
    RgbColor=f"{RedColorDecimal};{GreenColorDecimal};{BlueColorDecimal}"
    return f"{_ESCAPE_PREFIX}48;2;{RgbColor}m"
  else:
    raise ValueError(f"Invalid color specification ({Color})")
  return None

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to clear the screen
# Args: None
# Returns:
# - string: ANSI escape sequence to clear the screen
# ---------------------------------------------------------------------------------------------------------------------
def ClearScreen():
  return _CLEAR_SCREEN

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to move cursor to home position (top-left)
# Args: None
# Returns:
# - string: ANSI escape sequence for cursor home
# ---------------------------------------------------------------------------------------------------------------------
def CursorHome():
  return _CURSOR_GO_HOME

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to move cursor to an absolute position
# Args:
# - Row (int): Target row (1-based)
# - Col (int): Target column (1-based)
# Returns:
# - string: ANSI escape sequence to set cursor position
# ---------------------------------------------------------------------------------------------------------------------
def CursorSetPos(Row,Col):
  return _CURSOR_SET_POS.format(row=Row,col=Col)

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to move cursor relative to its current position
# Args:
# - RowDelta (int): Rows to move (positive=down, negative=up)
# - ColDelta (int): Columns to move (positive=right, negative=left)
# Returns:
# - string: ANSI escape sequence for relative cursor movement
# ---------------------------------------------------------------------------------------------------------------------
def CursorMove(RowDelta,ColDelta):
  Seq=""
  if ColDelta<0:
    Seq+=_CURSOR_MOVE_LEFT.format(n=-ColDelta)
  elif ColDelta>0:
    Seq+=_CURSOR_MOVE_RIGHT.format(n=ColDelta)
  if RowDelta<0:
    Seq+=_CURSOR_MOVE_UP.format(n=-RowDelta)
  elif RowDelta>0:
    Seq+=_CURSOR_MOVE_DOWN.format(n=RowDelta)
  return Seq

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to scroll the terminal up or down
# Args:
# - Lines (int): Lines to scroll (positive=up, negative=down)
# Returns:
# - string: ANSI escape sequence for scrolling, or empty string if Lines is 0
# ---------------------------------------------------------------------------------------------------------------------
def Scroll(Lines):
  if Lines>0:
    return _SCROLL_UP.format(n=Lines)
  elif Lines<0:
    return _SCROLL_DOWN.format(n=-Lines)
  else:
    return ""
    
# ---------------------------------------------------------------------------------------------------------------------
# Return the ANSI DSR sequence to query cursor position; terminal replies with \x1b[row;colR
# Args: None
# Returns:
# - string: ANSI escape sequence to query cursor position
# ---------------------------------------------------------------------------------------------------------------------
def QueryCursorPos():
  return _QUERY_CURSOR_POS

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence to reset all colors and attributes to default
# Args: None
# Returns:
# - string: ANSI escape sequence to reset colors
# ---------------------------------------------------------------------------------------------------------------------
def ResetColor():
  return _RESET_COLOR

# ---------------------------------------------------------------------------------------------------------------------
# Set alternative screen buffer (enables full-screen applications without affecting the main screen)
# Args: None
# Returns:
# - string: ANSI escape sequence to switch to the alternate screen buffer
# ---------------------------------------------------------------------------------------------------------------------
def EnterAltScreen():
  return _ENTER_ALT_SCREEN

# ---------------------------------------------------------------------------------------------------------------------
# Exits the alternative screen buffer and returns to the main screen
# Args: None
# Returns:
# - string: ANSI escape sequence to switch to the alternate screen buffer
# ---------------------------------------------------------------------------------------------------------------------
def ExitAltScreen():
  return _EXIT_ALT_SCREEN

# ---------------------------------------------------------------------------------------------------------------------
# Hides the cursor (useful for full-screen applications)
# Args: None
# Returns:
# - string: ANSI escape sequence to hide the cursor
# ---------------------------------------------------------------------------------------------------------------------
def HideCursor():
  return _HIDE_CURSOR

# ---------------------------------------------------------------------------------------------------------------------
# Shows the cursor (useful to restore visibility after hiding it)
# Args: None
# Returns:
# - string: ANSI escape sequence to show the cursor
# ---------------------------------------------------------------------------------------------------------------------
def ShowCursor():
  return _SHOW_CURSOR

# ---------------------------------------------------------------------------------------------------------------------
# Return a complete ANSI escape sequence by prepending the escape prefix to the given payload
# Args:
# - Payload (string): The sequence content to append after the escape prefix
# Returns:
# - string: Full ANSI escape sequence (prefix + payload)
# ---------------------------------------------------------------------------------------------------------------------
def Escape(Payload):
  return _ESCAPE_PREFIX+Payload