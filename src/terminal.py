# ---------------------------------------------------------------------------------------------------------------------
# terminal.py: Low level terminal I/O library for Kelwyn.
# ---------------------------------------------------------------------------------------------------------------------

# Functions in ths library:
# - SetRawTerminalMode()                      #Disables line buffering,echo,and Ctrl+C handling
# - RestoreTerminalMode()                     #Restores terminal mode saved by SetRawTerminalMode
# - KeyEvent=ReadKey()                        #Returns next key-down event,blocking until available
# - bool=IsKeyboardHit()                       #Returns True if there are pending keystrokes in the buffer
# - Write(Data)                               #Writes str or bytes to terminal output
# - Rows,Cols=GetTerminalSize()               #Returns terminal size,fallback (24,80)
# - ClearScreen(CursorPosition="bottom")      #Clears screen and place cursor at top or bottom
# - Row,Col=GetCursorPos()                    #Returns current cursor position as (row,col) 1-based
# - MoveCursorChars(Offset)                   #Moves cursor by N chars (positive=forward,negative=backward),wrapping lines

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import os
import sys
import ansi
import shutil
import platform
import subprocess
from dataclasses import dataclass
if platform.system()=="Windows":
  import ctypes
  import msvcrt
  from ctypes import Structure,Union,byref,c_long,c_short,windll
else:
  import select
  import termios
  import tty
import debug

# ---------------------------------------------------------------------------------------------------------------------
# General constants and variables
# ---------------------------------------------------------------------------------------------------------------------
IS_WINDOWS=(platform.system()=="Windows")
IS_LINUX=(platform.system()=="Linux")
IS_MACOS=(platform.system()=="Darwin")
_ForceLineBreak=True

# ---------------------------------------------------------------------------------------------------------------------
# Constants for windows
# ---------------------------------------------------------------------------------------------------------------------

#Win32 Console API constants
WIN_STD_INPUT  =ctypes.c_ulong(0xFFFFFFF6)  #(DWORD)-10
WIN_STD_OUTPUT =ctypes.c_ulong(0xFFFFFFF5)  #(DWORD)-11
WIN_KEY_EVENT  =0x0001
WIN_KEY_PRESSED=0x8000  #high bit set=key is down

#Generic modifier VK codes (used only to skip those events from ReadKey)
WIN_VK_SHIFT  =0x10
WIN_VK_CONTROL=0x11
WIN_VK_MENU   =0x12

#Left/right-specific VK codes for GetKeyState
WIN_VK_LSHIFT  =0xA0
WIN_VK_RSHIFT  =0xA1
WIN_VK_LCONTROL=0xA2
WIN_VK_RCONTROL=0xA3
WIN_VK_LMENU   =0xA4   #Left Alt
WIN_VK_RMENU   =0xA5   #Right Alt / AltGr

#Virtual key map for non-character keys and function keys
WIN_VK_MAP={
  0x08: "BACKSPACE",
  0x09: "TAB",
  0x0D: "RETURN",
  0x1B: "ESCAPE",
  0x20: "SPACE",
  0x21: "PAGE_UP",
  0x22: "PAGE_DOWN",
  0x23: "END",
  0x24: "HOME",
  0x25: "LEFT",
  0x26: "UP",
  0x27: "RIGHT",
  0x28: "DOWN",
  0x2D: "INSERT",
  0x2E: "DELETE",
  0x2C: "PRINT_SCREEN",
}
WIN_VK_MAP.update({0x70 + i: f"F{i + 1}" for i in range(12)})

# ---------------------------------------------------------------------------------------------------------------------
# Constants for Linux/macOS
# ---------------------------------------------------------------------------------------------------------------------

#These bytes are unambiguous named keys (not reported as Ctrl+x combos).
UNIX_PLAIN={
  0x08: "BACKSPACE",#^H  (old keyboards / some terminals)
  0x09: "TAB",     #^I
  0x0D: "RETURN",  #^M
  0x1B: "ESCAPE",  #used when _ByteToKey is called with bare ESC
  0x7F: "BACKSPACE",#DEL  (standard on modern Linux)
}

#Remaining control bytes → key letter,reported with ctrl=True.
UNIX_CTRL={
  0x00: "SPACE",  #Ctrl+Space / Ctrl+@
  **{
    n: chr(ord("A") + n-1)
    for n in range(1,27)
    if n not in (0x08,0x09,0x0D)  #Tab,Return,Backspace handled above
  },
  0x1C: "\\",
  0x1D: "]",
  0x1E: "^",
  0x1F: "_",
}

#CSI final-byte sequences: \x1b[<letter>  (or \x1b[1;<mod><letter>)
UNIX_CSI_LETTER={
  "A": "UP",
  "B": "DOWN",
  "C": "RIGHT",
  "D": "LEFT",
  "F": "END",
  "H": "HOME",
  "P": "F1",
  "Q": "F2",
  "R": "F3",
  "S": "F4",
  "Z": "TAB",#Shift+Tab (\x1b[Z) – shift flag forced below
}

#CSI tilde sequences: \x1b[<n>~
UNIX_CSI_TILDE={
  1:  "HOME",
  2:  "INSERT",
  3:  "DELETE",
  4:  "END",
  5:  "PAGE_UP",
  6:  "PAGE_DOWN",
  15: "F5",
  17: "F6",
  18: "F7",
  19: "F8",
  20: "F9",
  21: "F10",
  23: "F11",
  24: "F12",
}

#SS3 sequences: \x1bO<letter>
UNIX_SS3={
  "A": "UP",
  "B": "DOWN",
  "C": "RIGHT",
  "D": "LEFT",
  "F": "END",
  "H": "HOME",
  "M": "RETURN",
  "P": "F1",
  "Q": "F2",
  "R": "F3",
  "S": "F4",
}

#Kitty keyboard protocol – special Unicode codepoints
UNIX_KITTY_SPECIAL={
  9:     "TAB",
  13:    "RETURN",
  27:    "ESCAPE",
  127:   "BACKSPACE",
  57358: "CAPS_LOCK",
  57359: "SCROLL_LOCK",
  57360: "NUM_LOCK",
  57361: "PRINT_SCREEN",
  57362: "PAUSE",
  57363: "MENU",
}

# ---------------------------------------------------------------------------------------------------------------------
# Key event data class
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class KeyEvent:
  
  #Attributes
  Key: str=""
  Char: str|None=None
  Ctrl: bool=False
  Shift: bool=False
  Alt: bool=False
  AltGr: bool=False
  
  #Printable character flag
  def IsPrintable(self):
    return self.Char is not None
  
  #Key code string
  def Code(self):
    Parts=[]
    if self.Ctrl:
      Parts.append("CTRL")
    if self.Alt:
      Parts.append("ALT")
    if self.AltGr:
      Parts.append("ALTGR")
    if self.Shift:
      Parts.append("SHIFT")
    Parts.append(self.Key)
    return "+".join(Parts)

# ---------------------------------------------------------------------------------------------------------------------
# Windows – Win32 Console API via ctypes
# ---------------------------------------------------------------------------------------------------------------------

#Ctypes structures for ReadConsoleInputW (defined at module level to allow cross-references)
if IS_WINDOWS:
  class _UChar(Union): _fields_=[("UnicodeChar",ctypes.c_wchar),("AsciiChar",ctypes.c_char)]
  class _KeyEventRecord(Structure): _fields_=[("KeyDown",c_long),("RepeatCount",c_short),("VirtualKeyCode",c_short),("VirtualScanCode",c_short),("uChar",_UChar),("ControlKeyState",c_long)]
  class _MouseEventRecord(Structure): _fields_=[("MousePosition",c_short * 2),("ButtonState",c_long),("ControlKeyState",c_long),("EventFlags",c_long)]
  class _EventUnion(Union): _fields_=[("KeyEvent",_KeyEventRecord),("MouseEvent",_MouseEventRecord)]
  class _InputRecord(Structure): _fields_=[("EventType",c_short),("Event",_EventUnion)]
  class _COORD(Structure): _fields_=[("X",c_short),("Y",c_short)]
  class _SMALL_RECT(Structure): _fields_=[("Left",c_short),("Top",c_short),("Right",c_short),("Bottom",c_short)]
  class _CONSOLE_SCREEN_BUFFER_INFO(Structure): _fields_=[("dwSize",_COORD),("dwCursorPosition",_COORD),("wAttributes",ctypes.c_ushort),("srWindow",_SMALL_RECT),("dwMaximumWindowSize",_COORD)]

#Terminal input class for windows
class TerminalInputWindows:

  #Global properties
  HandleCache=None
  SavedMode=None

  #Class level initialization: configure GetKeyState return type at import time.
  windll.user32.GetKeyState.restype =c_short
  windll.user32.GetKeyState.argtypes=[ctypes.c_int]
  windll.user32.ToUnicodeEx.restype=ctypes.c_int

  # -------------------------------------------------------------------------------------------------------------------
  # New instance will throw exception; this class is not meant to be instantiated.
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  def __new__(cls):
    raise TypeError("TerminalInputWindows cannot be instantiated")

  # -------------------------------------------------------------------------------------------------------------------
  # Return True if the given virtual key is currently held down
  # Args:
  # - Vk (int): Virtual key code to test
  # Returns:
  # - bool: True if the key is pressed,False otherwise
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _Down(cls,Vk):
    return bool(ctypes.c_ushort(windll.user32.GetKeyState(Vk)).value&WIN_KEY_PRESSED)

  # -------------------------------------------------------------------------------------------------------------------
  # Return the current state of all modifier keys via GetKeyState
  # Args: None
  # Returns:
  # - tuple: (Shift,Ctrl,Alt,AltGr) as booleans reflecting the hardware state at the time of the call
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _Mod(cls):
    AltGr=cls._Down(WIN_VK_RMENU)
    Ctrl =(cls._Down(WIN_VK_LCONTROL) or cls._Down(WIN_VK_RCONTROL)) and not AltGr
    Alt  =cls._Down(WIN_VK_LMENU) and not AltGr
    Shift=cls._Down(WIN_VK_LSHIFT) or cls._Down(WIN_VK_RSHIFT)
    return Shift,Ctrl,Alt,AltGr

  # -------------------------------------------------------------------------------------------------------------------
  # Return True if a dead key is currently pending in the composition buffer
  # Args: None
  # Returns:
  # - bool: True if a dead key is pending (last event was a dead key press),False otherwise
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _HasDeadKeyPending(cls):
    KeyState=(ctypes.c_ubyte*256)()  #zeroed: no modifiers,no dead key override
    Buf=ctypes.create_unicode_buffer(4)
    Result=windll.user32.ToUnicodeEx(ctypes.c_uint(0x20),ctypes.c_uint(0x39),KeyState,Buf,ctypes.c_int(4),ctypes.c_uint(4),None)
    return not (Result==1 and Buf[0]==' ')

  # -------------------------------------------------------------------------------------------------------------------
  # Get and cache the Win32 console input handle for use with ReadConsoleInputW
  # Args: None
  # Returns:
  # - handle: Win32 console input handle
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _GetHandle(cls):
    
    #Get and cache console input handle
    if cls.HandleCache is None:
      
      #Stdin not redirected; use standard input handle directly
      if sys.stdin.isatty():
        cls.HandleCache=windll.kernel32.GetStdHandle(WIN_STD_INPUT)

      #stdin has been redirected,open the real console explicitly (_Fd not stored,process exit closes it)
      else:
        _Fd=os.open("CONIN$",os.O_RDWR | os.O_BINARY)
        cls.HandleCache=msvcrt.get_osfhandle(_Fd)

    #Returns handler
    return cls.HandleCache

  # -------------------------------------------------------------------------------------------------------------------
  # Switch the console to raw (no-echo,no-line) mode,disabling processed input,line input,and echo
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def SetRawTerminalMode(cls):
    Handle=cls._GetHandle()
    cls.SavedMode=ctypes.c_ulong(0)
    windll.kernel32.GetConsoleMode(Handle,byref(cls.SavedMode))
    windll.kernel32.SetConsoleMode(Handle,ctypes.c_ulong(0))

  # -------------------------------------------------------------------------------------------------------------------
  # Restore the console mode saved by SetRawTerminalMode
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def RestoreTerminalMode(cls):
    if cls.SavedMode is not None:
      windll.kernel32.SetConsoleMode(cls._GetHandle(),cls.SavedMode)

  # -------------------------------------------------------------------------------------------------------------------
  # Return True if there are pending key-down events in the console input buffer without consuming them
  # Uses PeekConsoleInputW to inspect queued events and applies the same filters as ReadKey
  # Args: None
  # Returns:
  # - bool: True if at least one actionable key-down event is waiting,False otherwise
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def IsKeyboardHit(cls):
    Handle=cls._GetHandle()
    TotalCount=ctypes.c_ulong(0)
    windll.kernel32.GetNumberOfConsoleInputEvents(Handle,byref(TotalCount))
    if TotalCount.value==0:
      return False
    NumPeek=min(TotalCount.value,32)
    Records=(_InputRecord*NumPeek)()
    PeekedCount=ctypes.c_ulong(0)
    windll.kernel32.PeekConsoleInputW(Handle,Records,ctypes.c_ulong(NumPeek),byref(PeekedCount))
    for i in range(PeekedCount.value):
      Rec=Records[i]
      if Rec.EventType!=WIN_KEY_EVENT:
        continue
      Ev=Rec.Event.KeyEvent
      if not bool(Ev.KeyDown):
        continue
      Vk=Ev.VirtualKeyCode
      if Vk in (WIN_VK_SHIFT,WIN_VK_CONTROL,WIN_VK_MENU,0xA0,0xA1,0xA2,0xA3,0xA4,0xA5):
        continue
      return True
    return False

  # -------------------------------------------------------------------------------------------------------------------
  # Block until a key-down event occurs and return a KeyEvent
  # Args: None
  # Returns:
  # - KeyEvent: Key event describing the pressed key and modifier state
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def ReadKey(cls):
    
    #Catch exceptions
    try:
    
      #Get console input handle and prepare input record buffer
      Handle=cls._GetHandle()
      Record=_InputRecord()
      Count =ctypes.c_ulong(0)

      #Read events until we get a key-down event with a valid key.
      while True:

        #Get next input event (blocks until an event is available).
        windll.kernel32.ReadConsoleInputW(Handle,byref(Record),ctypes.c_ulong(1),byref(Count))

        #Ignore non-key events and key-up events
        if Count.value==0 or Record.EventType!=WIN_KEY_EVENT:
          continue

        #Get event data
        Ev=Record.Event.KeyEvent
        Vk=Ev.VirtualKeyCode
        KeyDown=bool(Ev.KeyDown)

        #Skip modifier-only key events; modifiers are read via GetKeyState.
        if Vk in (WIN_VK_SHIFT,WIN_VK_CONTROL,WIN_VK_MENU,0xA0,0xA1,0xA2,0xA3,0xA4,0xA5):
          continue
        
        #Skip key-up events for non-modifier keys
        if not KeyDown:
          continue

        #Read actual hardware modifier state at this exact event.
        Shift,Ctrl,Alt,AltGr=cls._Mod()
        Uch=Ev.uChar.UnicodeChar

        #Skip dead key events: probe the composition buffer after the event was delivered.
        #If a dead key is pending,this event put it there → discard it; the next event carries the composed char.
        if not Ctrl and cls._HasDeadKeyPending():
          continue

        #Decode special keys
        if Vk in WIN_VK_MAP:
          Key=WIN_VK_MAP[Vk]
          Char=Uch if Uch and ord(Uch)>=0x20 else None
        
        #Decode letters A–Z (always uppercase)
        elif 0x41<=Vk<=0x5A:           
          Key=chr(Vk)
          Char=Uch if Uch and ord(Uch)>=0x20 else None
        
        #Decode digits 0-9
        elif 0x30<=Vk<=0x39:
          Key=chr(Vk)
          Char=Uch if Uch and ord(Uch)>=0x20 else None
        
        #Decode rest of printable ASCII (e.g. punctuation)
        elif Uch and ord(Uch)>=0x20:   #any other printable
          Key=Uch
          Char=Uch
        
        #Unknown / uninteresting event
        else:
          continue
        
        #Clear modifiers when char is not None
        #(on certain scenarios like when pasting text (crtl+v) modifier is seen enabled but keystroke is a regular char)
        if Char is not None:
          Ctrl=False
          Shift=False
          Alt=False
          AltGr=False

        #Return event
        return KeyEvent(Key=Key,Char=Char,Ctrl=Ctrl,Shift=Shift,Alt=Alt,AltGr=AltGr)
    
    #Interept KeyboardInterrupt as Ctrl+C key event so the shell can handle it (see comment in ReadConsoleInputW call above).
    except KeyboardInterrupt:
      return KeyEvent(Key="C",Ctrl=True)

  # -------------------------------------------------------------------------------------------------------------------
  # Return current cursor position as (Row,Col) 1-based using GetConsoleScreenBufferInfo
  # Args: None
  # Returns:
  # - tuple: (Row,Col) as 1-based integers relative to the visible window
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def GetCursorPos(cls):
    Handle=windll.kernel32.GetStdHandle(WIN_STD_OUTPUT)
    Info=_CONSOLE_SCREEN_BUFFER_INFO()
    windll.kernel32.GetConsoleScreenBufferInfo(Handle,byref(Info))
    Row=Info.dwCursorPosition.Y-Info.srWindow.Top+1
    Col=Info.dwCursorPosition.X+1
    return Row,Col

  # -------------------------------------------------------------------------------------------------------------------
  # Return the visible terminal window size as (Rows,Cols) using GetConsoleScreenBufferInfo
  # Args: None
  # Returns:
  # - tuple: (Rows,Cols) as integers reflecting the current visible window size
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def GetTerminalSize(cls):
    Handle=windll.kernel32.GetStdHandle(WIN_STD_OUTPUT)
    Info=_CONSOLE_SCREEN_BUFFER_INFO()
    windll.kernel32.GetConsoleScreenBufferInfo(Handle,byref(Info))
    Rows=Info.srWindow.Bottom-Info.srWindow.Top+1
    Cols=Info.srWindow.Right -Info.srWindow.Left+1
    return Rows,Cols

# ---------------------------------------------------------------------------------------------------------------------
# Linux / macOS – termios raw mode + VT100 / Kitty escape-sequence parser
# ---------------------------------------------------------------------------------------------------------------------

#Terminal input class for Unix/Linux/macOS
class TerminalInputUnix:

  #Saved terminal settings for restoration
  SavedTermios=None

  # -------------------------------------------------------------------------------------------------------------------
  # New instance will throw exception; this class is not meant to be instantiated.
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  def __new__(cls):
    raise TypeError("TerminalInputUnix cannot be instantiated")

  # -------------------------------------------------------------------------------------------------------------------
  # Read exactly one byte from the file descriptor,blocking until available
  # Args:
  # - Fd (int): File descriptor to read from
  # Returns:
  # - bytes: Single byte read from the file descriptor
  # -------------------------------------------------------------------------------------------------------------------
  @staticmethod
  def _Read1(Fd):
    return os.read(Fd,1)
  
  # -------------------------------------------------------------------------------------------------------------------
  # Read one byte from the file descriptor with a timeout; returns empty bytes if no data arrives in time
  # Args:
  # - Fd (int): File descriptor to read from
  # - Timeout (float,default 0.05): Maximum seconds to wait for data
  # Returns:
  # - bytes: Single byte read,or empty bytes if the timeout expired
  # -------------------------------------------------------------------------------------------------------------------
  @staticmethod
  def _Read1Timeout(Fd,Timeout=0.05):
    R,_,_=select.select([Fd],[],[],Timeout)
    return os.read(Fd,1) if R else b""

  # -------------------------------------------------------------------------------------------------------------------
  # Read a full UTF-8 character given the first byte already read
  # Args:
  # - Fd (int): File descriptor to read continuation bytes from
  # - First (bytes): First byte of the UTF-8 sequence already consumed
  # Returns:
  # - string: Decoded UTF-8 character
  # -------------------------------------------------------------------------------------------------------------------
  @staticmethod
  def _ReadUtf8(Fd,First):
    B0=First[0]
    if   B0<0x80: Extra=0
    elif B0<0xE0: Extra=1
    elif B0<0xF0: Extra=2
    else:         Extra=3
    Rest=os.read(Fd,Extra) if Extra else b""
    return (First + Rest).decode("utf-8",errors="replace")

  # -------------------------------------------------------------------------------------------------------------------
  # Decode an xterm modifier parameter (1-based) into (Shift,Alt,Ctrl) booleans
  # Args:
  # - M (int): Modifier parameter value (1-based,as sent in escape sequences)
  # Returns:
  # - tuple: (Shift,Alt,Ctrl) as booleans
  # -------------------------------------------------------------------------------------------------------------------
  @staticmethod
  def _DecodeMod(M):
    Bits=M-1
    return bool(Bits&1),bool(Bits&2),bool(Bits&4)

  #Escape-sequence parsers 
  # -------------------------------------------------------------------------------------------------------------------
  # Parse a CSI escape sequence after \x1b[ has been consumed
  # Args:
  # - Fd (int): File descriptor to read remaining sequence bytes from
  # Returns:
  # - KeyEvent: Parsed key event,or None if the sequence is unrecognized
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _ParseCsi(cls,Fd):
    
    #Is digit
    def _I(S):
      return int(S) if S.isdigit() else 0
    
    #Get input
    Buf=b""
    for _ in range(32):
      Ch=cls._Read1Timeout(Fd,0.1)
      if not Ch:
        break
      Buf += Ch
      if 0x40<=Ch[0]<=0x7E:  #final byte range
        break
    if not Buf:
      return None

    Final=chr(Buf[-1])
    ParamS=Buf[:-1].decode("ascii",errors="replace")
    Parts=ParamS.split(";") if ParamS else []

    #Kitty keyboard protocol: \x1b[<codepoint>;<mods>u
    if Final=="u":
      Cp =_I(Parts[0]) if Parts else 0
      Mod=_I(Parts[1]) if len(Parts)>=2 else 1
      S,A,C=cls._DecodeMod(Mod)
      if Cp in UNIX_KITTY_SPECIAL:
        Name=UNIX_KITTY_SPECIAL[Cp]
        Char=None
      elif Cp<0x20:
        Name=UNIX_CTRL.get(Cp,f"\\x{Cp:02x}")
        Char=None
      else:
        Ch  =chr(Cp)
        Name=Ch.upper() if Ch.isalpha() else Ch
        Char=Ch
      return KeyEvent(Key=Name,Char=Char,Ctrl=C,Shift=S,Alt=A)

    #Tilde sequences: \x1b[<n>~ or \x1b[<n>;<mod>~
    if Final=="~":
      N  =_I(Parts[0]) if Parts else 0
      Mod=_I(Parts[1]) if len(Parts)>=2 else 1
      S,A,C=cls._DecodeMod(Mod)
      Name=UNIX_CSI_TILDE.get(N)
      if Name is None:
        return None
      return KeyEvent(Key=Name,Ctrl=C,Shift=S,Alt=A)

    #Letter sequences: \x1b[A or \x1b[1;<mod>A
    if Final in UNIX_CSI_LETTER:
      Mod=_I(Parts[1]) if len(Parts)>=2 else 1
      S,A,C=cls._DecodeMod(Mod)
      Name=UNIX_CSI_LETTER[Final]
      if Final=="Z":   #Shift+Tab – no modifier byte needed
        S=True
      return KeyEvent(Key=Name,Ctrl=C,Shift=S,Alt=A)

    return None

  # -------------------------------------------------------------------------------------------------------------------
  # Parse an SS3 escape sequence after \x1bO has been consumed
  # Args:
  # - Fd (int): File descriptor to read the final byte from
  # Returns:
  # - KeyEvent: Parsed key event,or None if the sequence is unrecognized
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _ParseSs3(cls,Fd):
    Ch=cls._Read1Timeout(Fd,0.05)
    if not Ch:
      return None
    Name=UNIX_SS3.get(chr(Ch[0]))
    return KeyEvent(Key=Name) if Name else None

  # -------------------------------------------------------------------------------------------------------------------
  # Convert a raw byte (possibly the start of a UTF-8 sequence) to a KeyEvent
  # Args:
  # - Fd (int): File descriptor to read continuation bytes from if needed
  # - B (bytes): First byte already read from the terminal
  # Returns:
  # - KeyEvent: Parsed key event,or None if the byte is unrecognized
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def _ByteToKey(cls,Fd,B):

    #Plain key event if byte is in UNIX_PLAIN map
    Byte=B[0]
    if Byte in UNIX_PLAIN:
      return KeyEvent(Key=UNIX_PLAIN[Byte])

    #Control key event if byte is in UNIX_CTRL map
    if Byte<0x20 or Byte==0x7F:
      Name=UNIX_CTRL.get(Byte)
      return KeyEvent(Key=Name,Ctrl=True) if Name else None

    #Printable character – assemble full UTF-8 codepoint
    Char=cls._ReadUtf8(Fd,B)
    Name=Char.upper() if Char.isalpha() else Char
    return KeyEvent(Key=Name,Char=Char)

  # -------------------------------------------------------------------------------------------------------------------
  # Switch stdin to raw (no-echo,no-line-buffer) mode
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def SetRawTerminalMode(cls):
    Fd=sys.stdin.fileno()
    cls.SavedTermios=termios.tcgetattr(Fd)
    tty.setraw(Fd)

  # -------------------------------------------------------------------------------------------------------------------
  # Restore the terminal settings saved by SetRawTerminalMode
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def RestoreTerminalMode(cls):
    if cls.SavedTermios is not None:
      termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,cls.SavedTermios)

  # -------------------------------------------------------------------------------------------------------------------
  # Return True if there are bytes waiting on stdin without consuming them
  # Uses select with a zero timeout for an immediate non-blocking check
  # Args: None
  # Returns:
  # - bool: True if at least one byte is available to read,False otherwise
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def IsKeyboardHit(cls):
    Fd=sys.stdin.fileno()
    R,_,_=select.select([Fd],[],[],0)
    return bool(R)

  # -------------------------------------------------------------------------------------------------------------------
  # Block until a key is pressed and return a KeyEvent
  # Args: None
  # Returns:
  # - KeyEvent: Key event describing the pressed key and modifier state
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def ReadKey(cls):
    
    #Read bytes until we get a valid key event.
    Fd=sys.stdin.fileno()
    while True:
      B=cls._Read1(Fd)
      if not B:
        continue

      #Escape or start of escape sequence 
      if B[0]==0x1B:
        
        #Event is escape key
        NextB=cls._Read1Timeout(Fd,0.05)
        if not NextB:
          return KeyEvent(Key="ESCAPE")
        
        #CSI or SS3 sequence,or Alt+key combo
        Nb=NextB[0]
        if Nb==ord("["):
          Ev=cls._ParseCsi(Fd)
          if Ev is not None:
            return Ev
        elif Nb==ord("O"):
          Ev=cls._ParseSs3(Fd)
          if Ev is not None:
            return Ev
        else:
          Ev=cls._ByteToKey(Fd,NextB)
          if Ev is not None:
            Ev.Alt=True
            return Ev
      
      #Regular key or UTF-8 sequence
      else:
        Ev=cls._ByteToKey(Fd,B)
        if Ev is not None:
          return Ev

  # -------------------------------------------------------------------------------------------------------------------
  # Return current cursor position as (Row,Col) 1-based using the ANSI DSR sequence \x1b[6n
  # Args: None
  # Returns:
  # - tuple: (Row,Col) as 1-based integers,or None if the position could not be determined
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def GetCursorPos(cls):
    Fd=sys.stdin.fileno()
    OldAttr=termios.tcgetattr(Fd)
    InRaw=not (OldAttr[3] & termios.ICANON)
    if not InRaw:
      tty.setraw(Fd)
    try:
      sys.stdout.buffer.write(ansi.QueryCursorPos().encode("ascii"))
      sys.stdout.buffer.flush()
      Buf=b""
      for _ in range(32):
        R,_,_=select.select([Fd],[],[],0.5)
        if not R:
          break
        Ch=os.read(Fd,1)
        Buf+=Ch
        if Ch==b"R":
          break
    finally:
      if not InRaw:
        termios.tcsetattr(Fd,termios.TCSADRAIN,OldAttr)
    if Buf.startswith(b"\x1b[") and Buf.endswith(b"R"):
      try:
        Row,Col=Buf[2:-1].decode("ascii").split(";")
        return int(Row),int(Col)
      except Exception:
        return None
    return None

  # -------------------------------------------------------------------------------------------------------------------
  # Return terminal size as (Rows,Cols) using TIOCGWINSZ via shutil.get_terminal_size
  # Args: None
  # Returns:
  # - tuple: (Rows,Cols) as integers
  # -------------------------------------------------------------------------------------------------------------------
  @classmethod
  def GetTerminalSize(cls):
    Size=shutil.get_terminal_size(fallback=(24,80))
    return Size.lines,Size.columns

# ---------------------------------------------------------------------------------------------------------------------
# Set the terminal to raw mode by disabling line buffering,echo,and Ctrl+C handling
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def SetRawTerminalMode():
  if IS_WINDOWS:
    TerminalInputWindows.SetRawTerminalMode()
  else:
    TerminalInputUnix.SetRawTerminalMode()

# ---------------------------------------------------------------------------------------------------------------------
# Restore terminal mode saved by SetRawTerminalMode
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def RestoreTerminalMode():
  if IS_WINDOWS:
    TerminalInputWindows.RestoreTerminalMode()
  else:
    TerminalInputUnix.RestoreTerminalMode()

# ---------------------------------------------------------------------------------------------------------------------
# Return a KeyEvent for the next key-down event,blocking until one is available
# Args: None
# Returns:
# - KeyEvent: Key event describing the pressed key and modifier state
# ---------------------------------------------------------------------------------------------------------------------
def ReadKey():
  if IS_WINDOWS:
    return TerminalInputWindows.ReadKey()
  else:
    return TerminalInputUnix.ReadKey()

# ---------------------------------------------------------------------------------------------------------------------
# Return True if there are pending keystrokes in the input buffer,without consuming them
# Args: None
# Returns:
# - bool: True if at least one actionable keystroke is waiting, False otherwise
# ---------------------------------------------------------------------------------------------------------------------
def IsKeyboardHit():
  if IS_WINDOWS:
    return TerminalInputWindows.IsKeyboardHit()
  else:
    return TerminalInputUnix.IsKeyboardHit()

# ---------------------------------------------------------------------------------------------------------------------
# Set force line break mode
# Args:
# - Enabled (bool): If True,force a line break when the last terminal column is written
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def SetForceLineBreak(Enabled):
  global _ForceLineBreak
  _ForceLineBreak=Enabled

# ---------------------------------------------------------------------------------------------------------------------
# Write a string to the terminal output,encoding to UTF-8 and flushing immediately
# Args:
# - Str (string): Text to write to the terminal
# - Restore (bool,default False): If True,restore cursor position after writing)
# - Debug (bool,default True): If True,send debug log with cursor positions and other details about the write operation
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def Write(Str,Restore=False,Debug=True):
  
  #Get current cursor position
  CurPos=GetCursorPos()

  #Encode to bytes then write to stdout buffer and flush
  Bytes=Str.encode("utf-8",errors="replace")
  sys.stdout.buffer.write(Bytes)
  sys.stdout.buffer.flush()

  #Get new cursor position after write
  NewPos=GetCursorPos()
  
  #In case cursor is at last column and it advanced one less position than length of data,
  #move to next line to avoid overwriting the last character on next write.
  WroteExtraLine=False
  if _ForceLineBreak==True and CurPos[0]==NewPos[0] \
  and NewPos[1]==GetTerminalSize()[1] and NewPos[1]==CurPos[1]+(len(ansi.Strip(Str))-1)%GetTerminalSize()[1]:
    debug.Get().Send("terminal.Write(): Writting extra line, current cursos position: "+str(GetCursorPos()))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    NewPos=GetCursorPos()
    WroteExtraLine=True
    debug.Get().Send("terminal.Write(): Wrote extra line, current cursos position: "+str(GetCursorPos()))

  #Move cursor backwards same number of characters written if restore cursor position is requested
  RestorePos=None
  if Restore and len(ansi.Strip(Str))!=0:
    MoveCursorLinear(-len(ansi.Strip(Str)))
    RestorePos=GetCursorPos()

  #Debug log
  if Debug:
    debug.Get().Send(f"terminal.Write(): (Cur={str(CurPos).replace(" ","")} New={str(NewPos).replace(" ","")} EL={WroteExtraLine} Rest={str(RestorePos).replace(" ","")}) Str={Str!r}")
    #debug.Get().Send(f"terminal.Write(): (Cur={str(CurPos).replace(" ","")} New={str(NewPos).replace(" ","")} TC={TerminalCols} SW={SizeWritten} EL={WroteExtraLine} LW={LinesWritten},LM={LinesMoved},LS={LinesScrolled} Rest={str(RestorePos).replace(" ","")}) Str={Str!r}")

# ---------------------------------------------------------------------------------------------------------------------
# Return terminal size as (Rows,Cols) with a fallback of (24,80) if it cannot be determined
# Args: None
# Returns:
# - tuple: (Rows,Cols) as integers
# ---------------------------------------------------------------------------------------------------------------------
def GetTerminalSize():
  if IS_WINDOWS:
    return TerminalInputWindows.GetTerminalSize()
  else:
    return TerminalInputUnix.GetTerminalSize()

# ---------------------------------------------------------------------------------------------------------------------
# Move cursor by Offset characters,wrapping across lines (positive=forward,negative=backward)
# (important: Does not move cursor outside the visible window and will not produce scroll)
# Args:
# - Offset (int): Number of character positions to move (positive=forward,negative=backward)
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def MoveCursorLinear(Offset):
  Row,Col=GetCursorPos()
  Rows,Cols=GetTerminalSize()
  LinearPosition=(Row-1)*Cols+(Col-1)
  NewLinearPosition=max(0,min(Rows*Cols-1,LinearPosition+Offset))
  NewRow=NewLinearPosition//Cols+1
  NewCol=NewLinearPosition%Cols+1
  debug.Get().Send(f"terminal.MoveCursorLinear(): Offset={Offset} → CurPos={(Row,Col)} → NewPos=({(NewRow,NewCol)})")
  Write(ansi.CursorSetPos(NewRow,NewCol),Debug=False)

# ---------------------------------------------------------------------------------------------------------------------
# Return current cursor position as (Row,Col) 1-based
# Args: None
# Returns:
# - tuple: (Row,Col) as 1-based integers,or None if the position could not be determined
# ---------------------------------------------------------------------------------------------------------------------
def GetCursorPos():
  if IS_WINDOWS:
    return TerminalInputWindows.GetCursorPos()
  else:
    return TerminalInputUnix.GetCursorPos()

# ---------------------------------------------------------------------------------------------------------------------
# Sets cursor position to (Row,Col) 1-based
# Args: 
# - Row (int): Target row number (1-based)
# - Col (int): Target column number (1-based)
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def SetCursorPos(Row,Col):
  debug.Get().Send(f"terminal.SetCursorPos(): Moving cursor to ({Row},{Col})")
  Write(ansi.CursorSetPos(Row,Col),Debug=False)

# ---------------------------------------------------------------------------------------------------------------------
# Move cursor position relative to its current position
# Args:
# - ColDelta (int): Columns to move (positive=right,negative=left)
# - RowDelta (int): Rows to move (positive=down,negative=up)
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def MoveCursor(RowDelta,ColDelta):
  Write(ansi.CursorMove(RowDelta,ColDelta))

# ---------------------------------------------------------------------------------------------------------------------
# Clear the screen and position cursor at 'top' or 'bottom'
# Args:
# - CursorPosition (string,default "bottom"): Where to place cursor after clearing: "top" or "bottom"
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def ClearScreen(CursorPosition="bottom"):
  Rows,_=GetTerminalSize()
  Write(ansi.ClearScreen())
  if CursorPosition=="top":
    Write(ansi.CursorHome())
  else:
    Write(ansi.CursorSetPos(Rows,1))

# ---------------------------------------------------------------------------------------------------------------------
# Scroll the terminal screen up or down
# Args:
# - Lines (int): Lines to scroll (positive=up,negative=down)
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def Scroll(Lines):
  Write(ansi.Scroll(Lines))

# ---------------------------------------------------------------------------------------------------------------------
# Copy the given text to the system clipboard using platform-specific methods
# Args:
# - Text (string): Text to copy to the clipboard
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def ClipboardCopy(Text):
  if IS_WINDOWS:
    Command="clip"
  elif IS_LINUX:
    Command="xclip -selection clipboard"
  elif IS_MACOS:
    Command="pbcopy"
  subprocess.run(Command.split(" "),input=Text.encode(),check=True)

# ---------------------------------------------------------------------------------------------------------------------
# Enter alternative screen buffer,if supported by the terminal.
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def EnterAltScreen():
  Write(ansi.EnterAltScreen())

# ---------------------------------------------------------------------------------------------------------------------
# Exit alternative screen buffer,if supported by the terminal.
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def ExitAltScreen():
  Write(ansi.ExitAltScreen())

# ---------------------------------------------------------------------------------------------------------------------
# Hide the terminal cursor
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def HideCursor():
  Write(ansi.HideCursor())

# ---------------------------------------------------------------------------------------------------------------------
# Show the terminal cursor
# Args: None
# Returns: None
# ---------------------------------------------------------------------------------------------------------------------
def ShowCursor():
  Write(ansi.ShowCursor())