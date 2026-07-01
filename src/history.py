#Import libraries
import os
import terminal
import fnmatch

# ---------------------------------------------------------------------------
# Shell history
# ---------------------------------------------------------------------------
class ShellHistory:

  #Path marks in history file
  PATH_MARK_BEG="⟪ "
  PATH_MARK_END=" ⟫ "

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
    self.LastAddedPath=None
    self.LastAddedCommand=None
    self.AllCommands=[]
    self.PathCommands=[]
    self.GhostMatches=[]
    self.GhostSearchString=""
    
    #Load history
    History=[]
    if HistoryFile!=None and os.path.isfile(HistoryFile):
      with open(HistoryFile,"r",encoding="utf-8") as File:
        History=[Line.strip() for Line in File if Line.strip()]

    #Truncate history file to maximun commands
    if NoTruncate==False and len(History)>MaxCommands:
      with open(HistoryFile,"w",encoding="utf-8") as File:
        for Command in History[-MaxCommands:]:
          File.write(Command+"\n")
      Hisory=History[-MaxCommands:]
    
    #Filter non printable characters from commands
    History=[terminal.FilterNonPrintable(Cmd) for Cmd in History]

    #Load command history
    self.AllCommands=[]
    self.PathCommands=[]
    for Command in History:
      if Command.startswith(self.PATH_MARK_BEG)==True and Command.find(self.PATH_MARK_END)!=-1:
        Path=Command[2:Command.find(self.PATH_MARK_END)].strip()
        Command=Command[Command.find(self.PATH_MARK_END)+len(self.PATH_MARK_END):].strip()
      else:
        Path=None
        Command=Command.strip()
      self.AllCommands.append(Command)
      self.PathCommands.append({"path":Path,"cmd":Command})
  
  # -------------------------------------------------------------------------
  # Append a command to the in-memory list and persist it to the history file
  # Args:
  # - Command (string): Command string to store
  # - Path (string): Current working directory path
  # Returns: None
  # -------------------------------------------------------------------------
  def Store(self,Command,Path):
    Command=Command.strip()
    if len(Command)==0 or (Path==self.LastAddedPath and Command==self.LastAddedCommand):
      return
    self.AllCommands.append(Command)
    self.PathCommands.append({"path":Path,"cmd":Command})
    if self.HistoryFile!=None:
      with open(self.HistoryFile,"a",encoding="utf-8") as File:
        HistoryCommand=self.PATH_MARK_BEG+Path+self.PATH_MARK_END+Command
        File.write(HistoryCommand+"\n")
      self.LastAddedPath=Path
      self.LastAddedCommand=Command

  # <<c:\01Diego>> cd 75_repos
  
  # -------------------------------------------------------------------------
  # Return the list of stored command strings
  # Args: None
  # Returns:
  # - list: List of command strings in chronological order
  # -------------------------------------------------------------------------
  def GetCommands(self):
    return self.AllCommands

  # -------------------------------------------------------------------------
  # Gets specific ghost suggestion for command buffer
  # (preserves appearance order in history)
  # Args: 
  # - CmdBuffer (string): Current command buffer to find suggestions for
  # - Index (int): Index of the suggestion to return (0 for most recent match)
  # Returns:
  # - string: Suggested command string, or None if no match found
  # -------------------------------------------------------------------------
  def GetGhostSuggestion(self,CmdBuffer,Index):
    if CmdBuffer!=self.GhostSearchString:
      Path=os.getcwd()
      self.Matches1=list(dict.fromkeys([Cmd["cmd"][len(CmdBuffer):] for Cmd in reversed(self.PathCommands) if Cmd["cmd"].startswith(CmdBuffer) and Cmd["path"]==Path]))
      self.Matches2=list(dict.fromkeys([Cmd["cmd"][len(CmdBuffer):] for Cmd in reversed(self.PathCommands) if Cmd["cmd"].startswith(CmdBuffer) and Cmd["cmd"] not in self.Matches1]))
      self.GhostMatches=self.Matches1+self.Matches2
      self.GhostSearchString=CmdBuffer
      #print(f"\nPath: {Path}")
      #print(f"Ghost matches 1 for '{CmdBuffer}': {self.Matches1[:10]}{'...' if len(self.Matches1)>10 else ''}")
      #print(f"Ghost matches 2 for '{CmdBuffer}': {self.Matches2[:10]}{'...' if len(self.Matches2)>10 else ''}")
      #print(f"Ghost matches combined for '{CmdBuffer}': {self.GhostMatches[:10]}{'...' if len(self.GhostMatches)>10 else ''}")
    if len(self.GhostMatches)==0:
      return None
    return self.GhostMatches[Index%len(self.GhostMatches)]
  
  # -------------------------------------------------------------------------
  # Gets full list of ghost suggestions that match command buffer
  # (does not preserves appearance order in history, sorts alphabeticaly)
  # Args: 
  # - CmdBuffer (string): Current command buffer to find suggestions for
  # - SearchMode (string): "prefix" to match commands that start with buffer, "pattern" to match commands by wildcard pattern
  # Returns:
  # - list of string: Suggested commands, or None if no match found
  # -------------------------------------------------------------------------
  def GetAllGhostSuggestions(self,CmdBuffer,SearchMode):
    if SearchMode=="prefix":
      self.GhostMatches=sorted(list(set([Cmd for Cmd in self.AllCommands if Cmd.startswith(CmdBuffer)])))
    elif SearchMode=="pattern":
      Pattern1=CmdBuffer.strip().replace(" ","*")+"*"
      Pattern2="*"+CmdBuffer.strip().replace(" ","*")+"*"
      Matches1=sorted(list(set([Cmd for Cmd in self.AllCommands if fnmatch.fnmatch(Cmd,Pattern1)])))
      Matches2=sorted(list(set([Cmd for Cmd in self.AllCommands if fnmatch.fnmatch(Cmd,Pattern2) and Cmd not in Matches1])))
      self.GhostMatches=Matches1+Matches2
    return self.GhostMatches if len(self.GhostMatches)!=0 else None
