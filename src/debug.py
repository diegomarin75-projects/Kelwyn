#Import libraries
import os
import datetime
import traceback

#Module-level singleton instance
_DebugLog=None

# ---------------------------------------------------------------------------
# Initialize the module-level debug log singleton
# Args:
# - DebugLogFile (string): Path to the debug log file, or None to disable logging
# - MaxLines (int): Maximum number of lines to keep in the log file
# - NoTruncate (bool): If True, do not truncate the log file when it exceeds MaxLines
# - Config (dict): JSON Configuration file
# Returns: None
# ---------------------------------------------------------------------------
def Init(DebugLogFile,MaxLines,NoTruncate,Config):
  global _DebugLog
  _DebugLog=DebugLog(DebugLogFile,MaxLines,NoTruncate,Config)

# ---------------------------------------------------------------------------
# Return the module-level debug log singleton instance
# Args: None
# Returns:
# - DebugLog: The current debug log instance, or None if not initialized
# ---------------------------------------------------------------------------
def Get():
  return _DebugLog

# ---------------------------------------------------------------------------
# Debug log
# ---------------------------------------------------------------------------
class DebugLog:

  # -------------------------------------------------------------------------
  # Constructor
  # Args:
  # - DebugLogFile (string): Path to the debug log file, or None to disable logging
  # - MaxLines (int): Maximum number of lines to keep in the log file before truncating
  # - NoTruncate (bool): If True, do not truncate the log file when it exceeds MaxLines
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------
  def __init__(self,DebugLogFile,MaxLines,NoTruncate,Config):
    
    #Initialize debug log
    self.Config=Config
    self.DebugLogFile=DebugLogFile
    self.MaxLines=MaxLines

    #Truncate log file if it exceeds max lines
    if DebugLogFile!=None and os.path.isfile(DebugLogFile) and NoTruncate==False:
      with open(DebugLogFile,"r",encoding="utf-8") as File:
        Lines=File.readlines()
      if len(Lines)>MaxLines:
        with open(DebugLogFile,"w",encoding="utf-8") as File:
          File.writelines(Lines[-MaxLines:])
    
    #Signal start in debug log
    self.Send("-"*120, Raw=True)

  # -------------------------------------------------------------------------
  # Append a timestamped debug message to the log file
  # Args:
  # - Message (string): Message to log
  # Returns: None
  # -------------------------------------------------------------------------
  def Send(self,Message, Raw=False):
      
    #Append message to log file with timestamp and caller info
    if self.DebugLogFile!=None:
      with open(self.DebugLogFile,"a",encoding="utf-8") as File:
        if Raw:
          File.write(Message+"\n")
        else:
          Caller=traceback.extract_stack()[-3]
          CallerInfo=f"({os.path.basename(Caller.filename)}:{Caller.name}():{Caller.lineno})"
          TimeStamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          File.write(f"[{TimeStamp}] {CallerInfo} {Message}\n")