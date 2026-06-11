#Import libraries
import os
import getpass
import socket
import subprocess
import ansi
import const
import utils
import datetime
import debug
from pathlib import Path

# ---------------------------------------------------------------------------
# Prompt builder class
# ---------------------------------------------------------------------------
class PromptBuilder:

  # -------------------------------------------------------------------------
  # Constructor
  # Args:
  # - WhippetsFolder (string): Folder on which whippet modules are located
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------
  def __init__(self,WhippetsFolder,Config):
    
    #Get configuration
    self.Config=Config
    self.PromptString=Config.get("system_prompt",const.DEFAULT_PROMPT)
    self.GitCleanColor=Config.get("git_clean_color",const.DEFAULT_FOREGROUND_COLOR)
    self.GitDirtyColor=Config.get("git_dirty_color",const.DEFAULT_FOREGROUND_COLOR)
    self.GitConflictColor=Config.get("git_conflict_color",const.DEFAULT_FOREGROUND_COLOR)
    self.BetaModeColor=Config.get("beta_mode_color",const.DEFAULT_FOREGROUND_COLOR)

    #Load whippet modules
    self.Whippets={}
    for PythonFile in Path(WhippetsFolder).glob("*.py"):
      Module=utils.LoadPythonModule(PythonFile)
      if Module!=None and hasattr(Module,"Whippet"):
        Name=PythonFile.stem
        self.Whippets[Name]=Module.Whippet
    debug.Get().Send(f"Loaded whippet modules: {list(self.Whippets.keys())}")
  
  # -------------------------------------------------------------------------
  # Set the prompt template string
  # Args:
  # - PromptString (string): Prompt template string with placeholder tokens
  # Returns: None
  # -------------------------------------------------------------------------
  def Set(self,PromptString):
    self.PromptString=PromptString

  # -------------------------------------------------------------------------
  # Build and return the prompt string with all placeholders replaced
  # Args: None
  # Returns:
  # - string: Fully expanded prompt string ready to display
  # -------------------------------------------------------------------------
  def Get(self):
    
    #Get prompt string
    Prompt=self.PromptString

    #Replace whippets in prompt
    for Whippet in self.Whippets:
      if Prompt.find("<"+Whippet+">")!=-1:
        Prompt=Prompt.replace("<"+Whippet+">",self.Whippets[Whippet](self.Config))

    #Replace {%code%} by ANSI escape sequence
    if Prompt.find("{%")!=-1:
      while True:
        Start=Prompt.find("{%")
        if Start==-1:
          break
        End=Prompt.find("%}",Start)
        if End==-1:
          break
        Code=Prompt[Start+2:End]
        AnsiSequence=ansi.Escape(Code)
        Prompt=Prompt[:Start]+AnsiSequence+Prompt[End+2:]
    
    #Replace {{varname}} by environment variable values
    if Prompt.find("{{")!=-1:
      while True:
        Start=Prompt.find("{{")
        if Start==-1:
          break
        End=Prompt.find("}}",Start)
        if End==-1:
          break
        VarName=Prompt[Start+2:End]
        VarValue=os.environ.get(VarName,str(VarName).upper()+"!")
        Prompt=Prompt[:Start]+VarValue+Prompt[End+2:]
    
    #Return prompt
    return Prompt
