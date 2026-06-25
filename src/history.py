#Import libraries
import os
import terminal
import fnmatch

# ---------------------------------------------------------------------------
# Shell history
# ---------------------------------------------------------------------------
class ShellHistory:

  # -------------------------------------------------------------------------
  # Constructor
  # Args:
  # - HistoryFile (string): Path to the history file, or None to disable persistence
  # - MaxCommands (int): Maximum number of commands to retain in memory
  # - NoTruncate (bool): No truncation of history file
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------
  def __init__(self,HistoryFile,MaxCommands,NoTruncate,Config):
    
    #Get configuration
    self.Config=Config
    self.HistoryFile=HistoryFile
    self.MaxCommands=MaxCommands
    
    #Init variables
    self.LastAddedCommand=None
    self.Commands=[]
    self.GhostMatches=[]
    self.GhostSearchString=""
    
    #Load history
    if HistoryFile!=None and os.path.isfile(HistoryFile):
      with open(HistoryFile,"r",encoding="utf-8") as File:
        self.Commands=[Line.strip() for Line in File if Line.strip()]

    #Truncate history file to maximun commands
    if NoTruncate==False and len(self.Commands)>MaxCommands:
      with open(HistoryFile,"w",encoding="utf-8") as File:
        for Command in self.Commands[-MaxCommands:]:
          File.write(Command+"\n")
      self.Commands=self.Commands[-MaxCommands:]
    
    #Filter non printable characters from commands
    self.Commands=[terminal.FilterNonPrintable(Cmd) for Cmd in self.Commands]
  
  # -------------------------------------------------------------------------
  # Append a command to the in-memory list and persist it to the history file
  # Args:
  # - Command (string): Command string to store
  # Returns: None
  # -------------------------------------------------------------------------
  def Store(self,Command):
    Command=Command.strip()
    if len(Command)==0 or Command==self.LastAddedCommand:
      return
    self.Commands.append(Command)
    if self.HistoryFile!=None:
      with open(self.HistoryFile,"a",encoding="utf-8") as File:
        File.write(Command+"\n")
      self.LastAddedCommand=Command

  # -------------------------------------------------------------------------
  # Return the list of stored command strings
  # Args: None
  # Returns:
  # - list: List of command strings in chronological order
  # -------------------------------------------------------------------------
  def GetCommands(self):
    return self.Commands

  # -------------------------------------------------------------------------
  # Gets specific ghost suggestion for command buffer
  # Args: 
  # - CommandBuffer (string): Current command buffer to find suggestions for
  # - Index (int): Index of the suggestion to return (0 for most recent match)
  # Returns:
  # - string: Suggested command string, or None if no match found
  # -------------------------------------------------------------------------
  def GetGhostSuggestion(self,CommandBuffer,Index):
    if CommandBuffer!=self.GhostSearchString:
      self.GhostMatches=[Cmd[len(CommandBuffer):] for Cmd in reversed(self.Commands) if Cmd.startswith(CommandBuffer)]
      self.GhostSearchString=CommandBuffer
    if len(self.GhostMatches)==0:
      return None
    return self.GhostMatches[Index%len(self.GhostMatches)]
  
  # -------------------------------------------------------------------------
  # Gets full list of ghost suggestions that match command buffer
  # Args: 
  # - CommandBuffer (string): Current command buffer to find suggestions for
  # - SearchMode (string): "prefix" to match commands that start with buffer, "pattern" to match commands by wildcard pattern
  # Returns:
  # - list of string: Suggested commands, or None if no match found
  # -------------------------------------------------------------------------
  def GetAllGhostSuggestions(self,CommandBuffer,SearchMode):
    if SearchMode=="prefix":
      self.GhostMatches=sorted(list(set([Cmd for Cmd in self.Commands if Cmd.startswith(CommandBuffer)])))
    elif SearchMode=="pattern":
      Pattern1=CommandBuffer.strip().replace(" ","*")+"*"
      Pattern2="*"+CommandBuffer.strip().replace(" ","*")+"*"
      Matches1=sorted(list(set([Cmd for Cmd in self.Commands if fnmatch.fnmatch(Cmd,Pattern1)])))
      Matches2=sorted(list(set([Cmd for Cmd in self.Commands if fnmatch.fnmatch(Cmd,Pattern2) and Cmd not in Matches1])))
      self.GhostMatches=Matches1+Matches2
    return self.GhostMatches if len(self.GhostMatches)!=0 else None
