# ---------------------------------------------------------------------------------------------------------------------
# ansi.py: ANSI escape sequences
# ---------------------------------------------------------------------------------------------------------------------

# Functions in ths library:
# - AnsiColor(FgColor,BkColor=None): Returns ANSI escape sequence for given foreground and background colors.
# - Seq=QueryCursorPos()               #Returns DSR sequence; terminal replies with \x1b[row;colR

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
FD_BLACK  =30; BD_BLACK  =40; FB_BLACK  =90; BB_BLACK  =100;
FD_RED    =31; BD_RED    =41; FB_RED    =91; BB_RED    =101;
FD_GREEN  =32; BD_GREEN  =42; FB_GREEN  =92; BB_GREEN  =102;
FD_YELLOW =33; BD_YELLOW =43; FB_YELLOW =93; BB_YELLOW =103;
FD_BLUE   =34; BD_BLUE   =44; FB_BLUE   =94; BB_BLUE   =104;
FD_MAGENTA=35; BD_MAGENTA=45; FB_MAGENTA=95; BB_MAGENTA=105;
FD_CYAN   =36; BD_CYAN   =46; FB_CYAN   =96; BB_CYAN   =106;
FD_WHITE  =37; BD_WHITE  =47; FB_WHITE  =97; BB_WHITE  =107;
REVERSED  = 7; BOLD      = 1; UNDERLINE = 4;

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
# Return ANSI escape sequence for a standard foreground/background color
# Args:
# - FgColor (int or None): Foreground color code (ANSI color constant), or None for default
# - BkColor (int, default None): Background color code (ANSI color constant), or None for no background
# Returns:
# - string: ANSI escape sequence for the specified color
# ---------------------------------------------------------------------------------------------------------------------
def SetColor(FgColor,BkColor=None):
  FgStr=("0" if FgColor is None else str(FgColor))
  BkStr=(";"+str(BkColor) if BkColor is not None else "")
  return f"{_ESCAPE_PREFIX}{FgStr}{BkStr}m"

# ---------------------------------------------------------------------------------------------------------------------
# Return ANSI escape sequence for a 24-bit RGB color
# Args:
# - RgbColor (string): Color in #RRGGBB format, where RR, GG, BB are integers 00-FF
# - Mode (string, default "foreground"): "foreground" or "background"
# Returns:
# - string: ANSI escape sequence for the specified RGB color
# ---------------------------------------------------------------------------------------------------------------------
def SetRgb(RgbColor,Mode="foreground"):
  if not re.match(r'^#[0-9a-fA-F]{6}$',RgbColor):
    raise ValueError("Invalid RGB color format. Expected #RRGGBB.")
  RedColorDecimal=int(RgbColor[1:3],16)
  GreenColorDecimal=int(RgbColor[3:5],16)
  BlueColorDecimal=int(RgbColor[5:7],16)
  Color=f"{RedColorDecimal};{GreenColorDecimal};{BlueColorDecimal}"
  if Mode=="foreground":
    return f"{_ESCAPE_PREFIX}38;2;{Color}m"
  elif Mode=="background":
    return f"{_ESCAPE_PREFIX}48;2;{Color}m"

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

# ---------------------------------------------------------------------------------------------------------------------
# Strips ANSI escape sequences from a string, returning only the visible text content
# It removes only the ones used in this module
# Args:
# - Text (string): Text containing ANSI escape sequences
# Returns:
# - string: Input text with all ANSI escape sequences removed
# ---------------------------------------------------------------------------------------------------------------------
def Strip(Text):
  Regex=r'\x1b\[[0-9;]*[A-Za-z]'
  return re.sub(Regex,"",Text)
