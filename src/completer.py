#Import libraries
import os
import re
import getpass
import socket
import subprocess
from pathlib import Path
import ansi
import const
import utils
import debug
import parser
import terminal

#Constants
TOKEN_TAG="@token"
FALLBACK_COMPLETER_TYPE="fallback"

# ---------------------------------------------------------------------------
# Tab completer class
# ---------------------------------------------------------------------------
class TabCompleter:

  # -------------------------------------------------------------------------
  # Constructor
  # Args:
  # - CompletersFolder (string): Path to folder containing completer modules
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------
  def __init__(self,CompletersFolder,Config):
    
    #Get configuration
    self.Config=Config
    
    #Load available completer modules on completers folder
    self.Selectors={}
    for PythonFile in Path(CompletersFolder).glob("*.py"):
      Module=utils.LoadPythonModule(PythonFile)
      if Module!=None and hasattr(Module,"Selector"):
        for Selector in Module.Selector():
          self.Selectors[Selector["type"]]={"regex":Selector["regex"],"completer":Selector["completer"]}
    debug.Get().Send(f"Loaded completer modules: {list(self.Selectors.keys())}")

  # -------------------------------------------------------------------------
  # Substitute the token at the given offset in the command buffer with the token tag, and return the modified command and the token
  # Args:
  # - CommandBuffer (string): Original command buffer
  # - Tokens (list): List of tokens parsed from the command buffer
  # - Offset (int): Cursor offset in the command buffer
  # Returns:
  # - (string, dict): Tuple of modified command buffer with token tag and the token dict, or (None, None) if no token at offset is found
  # -------------------------------------------------------------------------
  def _SubstituteTokenAtOffset(self,CommandBuffer,Tokens,Offset):
    Found=False
    SearchString=None
    SearchToken=None
    for Token in Tokens:
      debug.Get().Send(f"Checking token: {Token!r} for offset: {Offset}")
      if Token["type"]=="string":
        if Offset-1>=Token["start"] and Offset-1<=Token["end"]:
          debug.Get().Send(f"Token at offset found: {Token!r}, substituting with '{TOKEN_TAG}'")
          SearchString=CommandBuffer[:Token["start"]]+TOKEN_TAG+CommandBuffer[Token["end"]+1:]
          SearchToken=Token
          Found=True
          break
      elif Token["type"]=="function":
        FuncSearchString,FuncSearchToken=self._SubstituteTokenAtOffset(CommandBuffer,Token["args"],Offset)
        if FuncSearchString!=None:
          SearchString=FuncSearchString
          SearchToken=FuncSearchToken
          Found=True
          break
    if Found==False:
      debug.Get().Send("No token at offset found for substitution")
      return None,None
    return SearchString,SearchToken

  # -------------------------------------------------------------------------
  # Get search string by substituing token at offset in command buffer by token tag
  # Args:
  # - CommandBuffer (string): Command line buffer to parse
  # Returns:
  # - (Tokens,Added) Tokens and added part to complete the command for parsing, or None if it cannot be parsed
  # -------------------------------------------------------------------------
  def _GetSearchString(self,CommandBuffer,Offset):

    #Get parser instance
    Parser=parser.CommandParser(self.Config)

    #Make command line to parse
    Added=""
    Iterations=0
    Command=CommandBuffer
    while Iterations<10:
      RetCode,Message,Tokens=Parser.Parse(Command)
      debug.Get().Send(f"Parser: Command={Command!r} Added={Added!r} RetCode={RetCode} Message={Message!r} Tokens={Tokens!r}")
      if RetCode==parser.PARSER_OK:
        break
      if RetCode==parser.PARSER_ERROR_UNMATCHED_PARENTHESIS:
        Command+=")"
        Added+=")"
      elif RetCode==parser.PARSER_ERROR_OPEN_QUOTED_STRING:
        Command+="\""
        Added+="\""
      else:
        break
      Iterations+=1
    
    #If command does not parse or there are no tokens, return None
    debug.Get().Send(f"Parser loop done: RetCode={RetCode} Message={Message!r} Tokens={Tokens!r}")
    if RetCode!=parser.PARSER_OK or len(Tokens)==0:
      debug.Get().Send("Command does not parse or there are no tokens, cannot get search string for completion")
      return None,None,None
    
    #Substite the token at offset with token tag
    SearchString,SearchToken=self._SubstituteTokenAtOffset(CommandBuffer,Tokens,Offset)
    
    #Return result
    return SearchString,SearchToken,Added

  # -------------------------------------------------------------------------
  # Complete a partial command or path for tab completion
  # Args:
  # - PartialCommandBuffer (string): Partial command buffer to complete
  # - Offset (int): Cursor offset in the command buffer
  # Returns:
  # - strings: Selected completion by user or None
  # -------------------------------------------------------------------------
  def Complete(self,CommandBuffer,Offset):
    
    #Get options from configuration
    CompleterMaximunHeightPercent=self.Config.get("completer_maximun_height_percent",const.DEFAULT_BOX_MAX_HEIGHT_PERCENT)
    CompleterOptionHighlightColor=self.Config.get("completer_option_highlight_color",const.DEFAULT_FOREGROUND_COLOR)
    CompleterOptionBackgroundColor=self.Config.get("completer_option_background_color",const.DEFAULT_BACKGROUND_COLOR)
    CompleterStatusForegroundColor=self.Config.get("completer_status_foreground_color",const.DEFAULT_FOREGROUND_COLOR)
    CompleterStatusBackgroundColor=self.Config.get("completer_status_background_color",const.DEFAULT_BACKGROUND_COLOR)
    
    #Calculate maximun option box height
    OptionBoxHeight=int(CompleterMaximunHeightPercent*terminal.GetTerminalSize()[0]/100)
    OptionBoxHeight=(terminal.GetTerminalSize()[0]-2 if OptionBoxHeight>terminal.GetTerminalSize()[0]-2 else OptionBoxHeight)
    
    #Get the search string by substituting the token at offset with token tag
    SearchString,SearchToken,Added=self._GetSearchString(CommandBuffer,Offset)
    if SearchString==None:
      return None
    debug.Get().Send(f"Search string for completion: {SearchString!r} Search token: {SearchToken!r} Added: {Added!r}")

    #Loop through selectors to find matches
    Matched=False
    Options=[]
    Completed=None
    for Selector in self.Selectors:

      #Get selector attributes
      Type=Selector
      Regex=self.Selectors[Selector]["regex"]
      Completer=self.Selectors[Selector]["completer"]
      
      #Continue if regex is None (i.e. fallback selector)
      if Regex is None:
        continue
      
      #Match the search string with the selector regex
      Match=re.match(Regex,SearchString)
      debug.Get().Send(f"Checking selector: Type={Type} Regex={Regex}, SearchString='{SearchString}', Matched={Match!=None}")
      if Match!=None:
        Matched=True
        Options=Completer(SearchToken["value"],self.Config)
        debug.Get().Send(f"Tab completer matched: Type={Type}, Options={Options}")
        break
    
    #Try fallback selector if no other selector matched
    if Matched==False:
      if FALLBACK_COMPLETER_TYPE in self.Selectors:
        Completer=self.Selectors[FALLBACK_COMPLETER_TYPE]["completer"]
        Options=Completer(SearchToken["value"],self.Config)
        debug.Get().Send(f"Fallback completer used: Options={Options}")
    
    #Get selected option
    SelectedOption=None
    if len(Options)==1:
      SelectedOption=Options[0]["value"]
    elif len(Options)>1:
      OptionBoxHeight=int(CompleterMaximunHeightPercent*terminal.GetTerminalSize()[0]/100)
      SelectedIndex=utils.SelectOption(Options,OptionBoxHeight,CompleterOptionHighlightColor,CompleterOptionBackgroundColor,"auto","",CompleterStatusForegroundColor,CompleterStatusBackgroundColor)
      if SelectedIndex!=None:
        SelectedOption=Options[SelectedIndex]["value"]
    if SelectedOption==None:
      return None
    
    #Complete the command buffer with the selected option
    SelectedOption=("\""+SelectedOption+"\"" if " " in SelectedOption else SelectedOption)
    Completed=SearchString.replace(TOKEN_TAG,SelectedOption,1)
    
    #Return completed command
    return Completed

