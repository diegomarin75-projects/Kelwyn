#Import libraries
import os
import json
import subprocess
import importlib.util
import const
import ansi
import terminal
import debug

# ----------------------------------------------------------------------------------
# Load a JSON configuration file that tolerates // comments and multiline strings.
# Args:
#   FilePath (str): Path to the JSON configuration file.
# Returns:
#   tuple[bool,str,dict | None]: Success flag,diagnostic message,and parsed JSON object.
# ----------------------------------------------------------------------------------------------------------------------
def JsonFileParser(FilePath):

  # ----------------------------------------------------------------------------------------------------------------------
  # Replaces new lines inside strings as \n (as standard JSON requires).
  # ----------------------------------------------------------------------------------------------------------------------
  def FixMultilineJson(Content):
    Output=[]
    StringMode=False
    EscapeMode=False
    for Char in Content:
      if StringMode:
        if EscapeMode:
          Output.append(Char)
          EscapeMode=False
        elif Char=="\\":
          Output.append(Char)
          EscapeMode=True
        elif Char=='"':
          Output.append(Char)
          StringMode=False
        elif Char=="\n":
          Output.append("\\n")
        else:
          Output.append(Char)
      else:
        if Char=='"':
          Output.append(Char)
          StringMode=True
        else:
          Output.append(Char)
    return "".join(Output)

  #Load JSON file
  #(comment lines are replaced with empty lines to preserve line numbering for error messages)
  try:
    FileHnd=open(FilePath,"r",encoding="utf-8")
    FileContent=FileHnd.read()
    FileHnd.close()
    FileContent="\n".join([(Line if Line.strip().startswith("//")==False else "") for Line in FileContent.split("\n")])
    FileContent=FixMultilineJson(FileContent)
    JsonObj=json.loads(FileContent)
  except Exception as Ex:
    Message=f"Exception reading configuration file ({FilePath}): {str(Ex)}"
    return False,Message,None

  #Return result
  return True,"",JsonObj
  
# ---------------------------------------------------------------------------
# Checks file path is accessible
# Args:
# - FilePath (string): File or directory path to check
# - QuickMode (bool): Does not check actual access for files only folders (much quicker)
# Returns:
# - bool: True if the path is accessible (can be read), False if not accessible (e.g. due to permissions)
# ---------------------------------------------------------------------------
def IsAccessible(FilePath,QuickMode=False):
  if FilePath.endswith(os.sep):
    try:
      os.listdir(FilePath)
      return True
    except PermissionError:
      return False
  else:
    if QuickMode==True:
      return True
    else:
      try:
        with open(FilePath,"rb"):
          pass
        return True
      except PermissionError:
        return False

# ---------------------------------------------------------------------------
# Execute a command and return its output and return code
# Args:
# - Command (string): Command to execute as a string
# - Redirect (bool, default False): Whether to capture and return command output (stdout and stderr combined)
# - Detached (bool, default False): Whether to launch process as detached
# - Timeout (float, default None): Timeout in seconds for command execution, or None for no timeout
# Returns:
# - int: Command return code (0 for success, -1 Keyboard interrupt, -2 Timeout, >0 Error)
# - string: Command output when Redirect is True, Process Pid when Detached is True, else None
# ---------------------------------------------------------------------------
def Exec(Command,Redirect=True,Detached=False,Timeout=None):
  try:
    if Redirect==True:
      Proc=subprocess.Popen(Command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8")
      if Timeout!=None:
        try:
          Output=Proc.communicate(timeout=Timeout)[0]
        except subprocess.TimeoutExpired:
          Proc.kill()
          Output=Proc.communicate()[0]
          return -2,Output
      else:
        Output=Proc.communicate()[0]
      ReturnCode=Proc.returncode
      return ReturnCode,Output
    elif Detached==True:
      Proc=subprocess.Popen(Command,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
      return 0,str(Proc.pid)
    else:
      ReturnCode=subprocess.call(Command,shell=True,encoding="utf-8")
      return ReturnCode,None
  except KeyboardInterrupt:
    Output=("Command execution interrupted by user" if Redirect else None)
    return -1,Output
  except Exception as Ex:
    Output=f"Command execution exception: {Ex}"
    return -1,Output

# -------------------------------------------------------------------------
# Load python module from a given file path
# Args:
# - FilePath (Path): Path to the completer module file
# Returns:
# - module: Loaded completer module
# -------------------------------------------------------------------------
def LoadPythonModule(FilePath):
  try:
    Spec=importlib.util.spec_from_file_location(FilePath.stem,FilePath)
    Module=importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
  except Exception as Ex:
    debug.Get().Send(f"Error loading module from {FilePath}: {str(Ex)}")
    return None
  return Module

# ---------------------------------------------------------------------------
# Display menu of options and get user selection
# (displays list of available options below the current line, scrolls if needed up to MaxVisible, and returns the selected option
# useful for tab completion or other interactive selection)
# Args:
# - InputOptions (list of dict): List of options, where each option is a dict with keys:
#   - "text" (string): Text to display for the option
#   - "color" (string): Color for the option in #RRGGBB format
# - MaxLines (int): Maximum number of lines to display for options (if more options than MaxLines*OptionsPerLine, will scroll)
# - HighlightColor (string): Color to use for highlighting the selected option in #RRGGBB format
# - BackgroundColor (string, default None): Optional background color for options in #RRGGBB format (if None, no background color is applied)
# - PrintStatus (string): Whether to print status row ("auto" printed only when option count exceeds visible options, "always" always print, "never" never print)
# - StatusText (string): Text to display in the status row
# - StatusForeColor (string): Foreground color for status row text in #RRGGBB format
# - StatusBackColor (string): Background color for status row in #RRGGBB format
# Returns:
# - int: Index of the selected option in the Options list, or None if no selection was made (e.g. user pressed Esc)
# ---------------------------------------------------------------------------
def SelectOption(InputOptions,MaxLines,HighlightColor,BackgroundColor=None,PrintStatus="auto",StatusText="",StatusForeColor=const.DEFAULT_FOREGROUND_COLOR,StatusBackColor=const.DEFAULT_BACKGROUND_COLOR):
  
  #Get option text with ANSI color codes, applying highlight mode
  def GetOption(Opt,Width,Color,Highlight):
    OptionText=Opt["text"]
    if Highlight==True:
      OptionText=">"+OptionText[1:]
    else:
      OptionText=" "+OptionText[1:]
    OptionText=OptionText.ljust(Width)
    return ansi.SetRgb(Opt["color"])+Color+OptionText+ansi.ResetColor()
  
  #Print options for current offset
  def PrintOptions(Options,FirstOptionRow,OptionOffset,VisibleLines,OptionsPerLine,OptionWidth,TerminalCols,BackColor):
    RawOptions=""
    terminal.SetCursorPos(FirstOptionRow,1)
    for RowIndex in range(VisibleLines):
      RawLine=""
      for ColIndex in range(OptionsPerLine):
        OptionIndex=OptionOffset+(RowIndex*OptionsPerLine)+ColIndex
        if OptionIndex<len(Options):
          Opt=Options[OptionIndex]
          RawLine+=GetOption(Opt,OptionWidth,BackColor,False)
        else:
          RawLine+=" "*OptionWidth
      RestSpaces=TerminalCols-len(ansi.Strip(RawLine))
      RawLine+=RestSpaces*" "
      RawOptions+=RawLine
    terminal.Write(RawOptions)

  
  #Display status row (status text plus selected option index and total options)
  def PrintStatusRow(StatusText,Options,SelectedIndex,TerminalCols,StatusRow,StatusForeColor,StatusBackColor):
    SelectedOptionText=f" {str(SelectedIndex+1)}/{len(Options)} "
    StatusTextAdjusted=" "+StatusText.strip()+" "
    StatusTextAdjusted=StatusTextAdjusted[:TerminalCols-len(SelectedOptionText)-2]+"\u2026" if len(StatusTextAdjusted)>TerminalCols-len(SelectedOptionText)-2 else StatusTextAdjusted
    StatusLine=f"{StatusTextAdjusted+" "*(TerminalCols-len(StatusTextAdjusted)-len(SelectedOptionText))+SelectedOptionText}"
    terminal.SetCursorPos(StatusRow,1)
    terminal.Write(ansi.SetRgb(StatusForeColor)+ansi.SetRgb(StatusBackColor,"background")+StatusLine.ljust(TerminalCols)+ansi.ResetColor())

  #If no options, return None
  if not InputOptions:
    return None
  
  #Catch exceptions to ensure cursor is shown again and line break is forced on exit
  try:
  
    #Hide cursor and do not force ending line break when writting to the last terminal column
    terminal.HideCursor()
    terminal.SetForceLineBreak(False)
    
    #Set HighlightColor and BackgroundColor ANSI strings
    HighColor=ansi.SetRgb(HighlightColor,"background")
    if BackgroundColor!=None:
      BackColor=ansi.SetRgb(BackgroundColor,"background")
    else:
      BackColor=""
    
    #Get current cursor position to restore after menu is exited
    RestoreRow,RestoreCol=terminal.GetCursorPos()
    debug.Get().Send(f"SelectOption: RestoreRow={RestoreRow}, RestoreCol={RestoreCol}, TerminalSize={terminal.GetTerminalSize()}, OptionsCount={len(InputOptions)}")
    
    #Calculate maximun option width, if longer than terminal width, truncate options and add ellipsis
    TerminalRows,TerminalCols=terminal.GetTerminalSize()
    Options=[{"text":" "+Opt["text"].strip()+" ","color":Opt["color"]} for Opt in InputOptions]
    MaxOptionLength=max(len(Opt["text"]) for Opt in Options)
    if MaxOptionLength>TerminalCols-1:
      Options=[
        {"text":Opt["text"][:TerminalCols-2]+"\u2026" if len(Opt["text"])>TerminalCols-1 else Opt["text"],"color":Opt["color"]} 
        for Opt in Options
      ]
      MaxOptionLength=TerminalCols-1

    #Calculate options per line, option width, total lines needed, visible lines and scroll lines
    OptionsPerLine=max(1,TerminalCols//MaxOptionLength)
    OptionWidth=TerminalCols//OptionsPerLine
    TotalLines=(len(Options)//OptionsPerLine)+(1 if len(Options)%OptionsPerLine>0 else 0)
    VisibleLines=min(TotalLines,MaxLines)
    MaxDisplayedOptions=(len(Options) if VisibleLines*OptionsPerLine>=len(Options) else VisibleLines*OptionsPerLine)
    StatusLine=(1 if PrintStatus=="always" or (PrintStatus=="auto" and TotalLines>VisibleLines) else 0)
    ScrollLines=(0 if RestoreRow+VisibleLines+StatusLine<TerminalRows else RestoreRow+VisibleLines+StatusLine-TerminalRows)
    debug.Get().Send(f"SelectOption: MaxOptionLength={MaxOptionLength}, OptionsPerLine={OptionsPerLine}, OptionWidth={OptionWidth}, TotalLines={TotalLines}, VisibleLines={VisibleLines}, ScrollLines={ScrollLines}, MaxDisplayedOptions={MaxDisplayedOptions}")

    #Make blank lines if needed to ensure we have space to display options
    terminal.Write("\n"*(VisibleLines+StatusLine))

    #Update restore row, and calculate first option row and status row
    RestoreRow+=(-ScrollLines if RestoreRow+VisibleLines+StatusLine>=TerminalRows else 0)
    FirstOptionRow=RestoreRow+1
    StatusRow=RestoreRow+VisibleLines+StatusLine
    debug.Get().Send(f"SelectOption: Updated RestoreRow={RestoreRow}, FirstOptionRow={FirstOptionRow}")
    
    #Display options
    OptionOffset=0
    PrintOptions(Options,FirstOptionRow,OptionOffset,VisibleLines,OptionsPerLine,OptionWidth,TerminalCols,BackColor)
    if StatusLine==1:
      PrintStatusRow(StatusText,Options,0,TerminalCols,StatusRow,StatusForeColor,StatusBackColor)

    #Highlight first menu option
    terminal.SetCursorPos(FirstOptionRow,1)
    terminal.Write(GetOption(Options[0],OptionWidth,HighColor,True), Restore=True)

    #Loop to read user input and update selection
    SelectedIndex=0
    PrevSelectedIndex=0
    PrevOptionOffset=0
    while True:
      
      #Read user key
      Key=terminal.ReadKey()
      
      #Handle special keys for selection (arrows, tab, enter, escape)
      if Key.Code()=="DOWN":
        SelectedIndex+=OptionsPerLine
        if SelectedIndex>MaxDisplayedOptions-1 or OptionOffset+SelectedIndex>len(Options)-1:
          SelectedIndex-=OptionsPerLine
          if OptionOffset+(VisibleLines*OptionsPerLine)<=len(Options)-1:
            OptionOffset+=OptionsPerLine
            if OptionOffset+SelectedIndex>len(Options)-1:
              SelectedIndex-=OptionsPerLine
      elif Key.Code()=="UP":
        SelectedIndex-=OptionsPerLine
        if SelectedIndex<0:
          SelectedIndex+=OptionsPerLine
          if OptionOffset>0:
            OptionOffset-=OptionsPerLine
      elif Key.Code()=="RIGHT" or Key.Code()=="TAB":
        SelectedIndex+=1
        if SelectedIndex>MaxDisplayedOptions-1 or OptionOffset+SelectedIndex>len(Options)-1:
          if OptionOffset+(VisibleLines*OptionsPerLine)<=len(Options)-1:
            OptionOffset+=OptionsPerLine
            SelectedIndex-=OptionsPerLine
        if OptionOffset+SelectedIndex>len(Options)-1:
          SelectedIndex=0
          OptionOffset=0
      elif Key.Code()=="LEFT" or Key.Code()=="SHIFT+TAB":
        SelectedIndex-=1
        if SelectedIndex<0:
          if OptionOffset>0:
            OptionOffset-=OptionsPerLine
            SelectedIndex+=OptionsPerLine
          else:
            OptionOffset=max(0,TotalLines-VisibleLines)*OptionsPerLine
            SelectedIndex=len(Options)-1-OptionOffset
      elif Key.Code()=="PAGE_DOWN":
        SelectedIndex+=OptionsPerLine*VisibleLines
        if SelectedIndex>MaxDisplayedOptions-1 or OptionOffset+SelectedIndex>len(Options)-1:
          SelectedIndex-=OptionsPerLine*VisibleLines
          if OptionOffset+2*(VisibleLines*OptionsPerLine)<=len(Options)-1:
            OptionOffset+=OptionsPerLine*VisibleLines
            if OptionOffset+SelectedIndex>len(Options)-1:
              SelectedIndex-=OptionsPerLine*VisibleLines
          else:
            OptionOffset=max(0,TotalLines-VisibleLines)*OptionsPerLine
            SelectedIndex=len(Options)-1-OptionOffset
      elif Key.Code()=="PAGE_UP":
        SelectedIndex-=OptionsPerLine*VisibleLines
        if SelectedIndex<0:
          SelectedIndex+=OptionsPerLine*VisibleLines
          if OptionOffset-VisibleLines*OptionsPerLine>=0:
            OptionOffset-=OptionsPerLine*VisibleLines
          else:
            OptionOffset=0
            SelectedIndex=0
      elif Key.Code()=="HOME":
        SelectedIndex=0
        OptionOffset=0
      elif Key.Code()=="END":
        OptionOffset=max(0,TotalLines-VisibleLines)*OptionsPerLine
        SelectedIndex=len(Options)-1-OptionOffset
      elif Key.Code()=="RETURN":
        break
      elif Key.Code()=="ESCAPE":
        SelectedIndex=None
        break

      #Debug log for key press and selection state
      debug.Get().Send(f"SelectOption: Key={Key.Code()}, SelectedIndex={SelectedIndex}, OptionOffset={OptionOffset}, MaxDisplayedOptions={MaxDisplayedOptions}, Len(Options)={len(Options)}")
      
      #Update displayed options if offset changed
      if OptionOffset!=PrevOptionOffset:
        debug.Get().Send(f"SelectOption: Updating displayed options for OptionOffset={OptionOffset}")
        PrintOptions(Options,FirstOptionRow,OptionOffset,VisibleLines,OptionsPerLine,OptionWidth,TerminalCols,BackColor)

      #If selection changed, update highlight
      if SelectedIndex!=PrevSelectedIndex or OptionOffset!=PrevOptionOffset:
        debug.Get().Send(f"SelectOption: Updating highlight for SelectedIndex={SelectedIndex}, PrevSelectedIndex={PrevSelectedIndex}, OptionOffset={OptionOffset}, PrevOptionOffset={PrevOptionOffset}")
        
        #Remove highlight from old selection
        if OptionOffset==PrevOptionOffset:
          OldOptionRow=FirstOptionRow+(PrevSelectedIndex//OptionsPerLine)
          OldOptionCol=((PrevSelectedIndex%OptionsPerLine)*OptionWidth)+1
          terminal.SetCursorPos(OldOptionRow,OldOptionCol)
          terminal.Write(GetOption(Options[OptionOffset+PrevSelectedIndex],OptionWidth,BackColor,False))
        
        #Highlight to new selection
        NewOptionRow=FirstOptionRow+(SelectedIndex//OptionsPerLine)
        NewOptionCol=((SelectedIndex%OptionsPerLine)*OptionWidth)+1
        terminal.SetCursorPos(NewOptionRow,NewOptionCol)
        terminal.Write(GetOption(Options[OptionOffset+SelectedIndex],OptionWidth,HighColor,True))
        if StatusLine==1:
          PrintStatusRow(StatusText,Options,OptionOffset+SelectedIndex,TerminalCols,StatusRow,StatusForeColor,StatusBackColor)
      
      #Update previous selected index and offset
      PrevSelectedIndex=SelectedIndex
      PrevOptionOffset=OptionOffset

    #Restore cursor position and clear options from terminal
    terminal.SetCursorPos(RestoreRow,RestoreCol)
    terminal.Write("".join(["\n"+" "*TerminalCols for _ in range(VisibleLines+StatusLine)]))
    terminal.SetCursorPos(RestoreRow,RestoreCol)
  
  #Exception handler
  except Exception as Ex:
    debug.Get().Send(f"SelectOption: Exception occurred: {str(Ex)}")
    terminal.SetForceLineBreak(True)
    terminal.ShowCursor()
    return None
  
  #Ensure cursor is shown again and line break is forced on exit
  finally:
    terminal.SetForceLineBreak(True)
    terminal.ShowCursor()

  #Return selected option
  return None if SelectedIndex==None else OptionOffset+SelectedIndex
