#Import libraries
import os
import sys
import argparse
import ansi
import const
import debug
import terminal
import shell
import config
import utils
from pathlib import Path

# ---------------------------------------------------------------------------
# Argument parser
# Args:
# - Version (string): version number of the application
# Returns:
# - args: parsed command line arguments
# - parser: Argument parser
# ---------------------------------------------------------------------------
def GetCommandLineArgs(Version):
  ArgParser=argparse.ArgumentParser(description=f"{const.APP_NAME} - A cross-platform command-line shell interpreter (v{Version})",add_help=True)
  RunGroup=ArgParser.add_mutually_exclusive_group()
  RunGroup.add_argument("--run",dest="Run",action="store_true",help="Start the shell",default=False)
  RunGroup.add_argument("--command",dest="Command",type=str,metavar="CMD",help="Execute a command and exit",default=None)
  ArgParser.add_argument("--config",dest="ConfigFile",type=str,metavar="PATH",help="Path to config file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--history",dest="HistoryFile",type=str,metavar="PATH",help="Path to history file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--debug-log",dest="DebugLogFile",type=str,metavar="PATH",help="Path to debug log file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--skip-init",dest="SkipInit",action="store_true",help="Skip the init script (use with --run or --command)",default=False)
  ArgParser.add_argument("--init-command",dest="InitCommand",type=str,metavar="CMD",help="Command to execute at startup (use with --run)",default=None)
  ArgParser.add_argument("--init-script",dest="InitScript",type=str,metavar="PATH",help="Path to init script to execute at startup (use with --run)",default=None)
  ArgParser.add_argument("--debug-kb",dest="DebugKb",action="store_true",help="Enters keyboard debugging mode",default=False)
  Args=ArgParser.parse_args()
  return Args,ArgParser
  
# ---------------------------------------------------------------------------
# Start shell interpreter
# Args:
# - MainFilePath (string): path to the main python file
# - Version (string): version number of the application
# - Args (argparse.Namespace): parsed command line arguments
# Returns:
# - bool: Indicates if shell is to be restarted (True) or not (False)
# ---------------------------------------------------------------------------
def StartShell(MainFilePath,Version,Args):

  #Get config file
  if Args.ConfigFile!=None:
    ConfigFile=Args.ConfigFile
  elif const.CONFIG_VAR_NAME in os.environ:
    ConfigFile=os.environ[const.CONFIG_VAR_NAME]
  else:
    ConfigFile=Path(os.path.dirname(os.path.abspath(MainFilePath))).parent / "cfg" / const.CONFIG_FILE

  #Load config file
  Status,Message=config.Load(ConfigFile)
  if Status==False:
    print("Error loading config file: "+Message)
    sys.exit(1)
  config.Get()["config_file_path"]=ConfigFile
  config.Get()["version"]=Version
  config.Get()["main_file_path"]=MainFilePath
  
  #Get history file
  if Args.HistoryFile!=None:
    HistoryFile=Args.HistoryFile
  elif "history_file" in config.Get():
    HistoryFile=config.Get()["history_file"]
  elif const.HISTORY_VAR_NAME in os.environ:
    HistoryFile=os.environ[const.HISTORY_VAR_NAME]  
  else:
    HistoryFile=Path(os.path.dirname(os.path.abspath(MainFilePath))).parent / const.HISTORY_FILE
  
  #Get debug log file
  if Args.DebugLogFile!=None:
    DebugLogFile=Args.DebugLogFile
  elif "debug_log_file" in config.Get():
    DebugLogFile=config.Get()["debug_log_file"]
  if const.DEBUG_LOG_VAR_NAME in os.environ:
    DebugLogFile=os.environ[const.DEBUG_LOG_VAR_NAME]
  else:
    DebugLogFile=Path(os.path.dirname(os.path.abspath(MainFilePath))).parent / const.DEBUG_LOG_FILE
  
  #Setup other configuration variables
  CommandsFolder=os.path.join(os.path.dirname(MainFilePath),"commands")
  CompletersFolder=os.path.join(os.path.dirname(MainFilePath),"completers")
  WhippetsFolder=os.path.join(os.path.dirname(MainFilePath),"whippets")
  MaxDebugLines=config.Get().get("max_debug_lines",const.MAX_DEBUG_LINES)
  MaxHistoryCommands=config.Get().get("max_history_commands",const.MAX_HISTORY_COMMANDS)

  #If executed for single command avoid truncation (debug log and history)
  NoTruncate=(True if Args.Command!=None else False)
  
  #Initialize debug log
  debug.Init(DebugLogFile,MaxLines=MaxDebugLines,NoTruncate=NoTruncate)

  #Signal start in debug log
  debug.Get().Send(f"{const.APP_NAME} v{Version} started ({"command mode: "+Args.Command if Args.Command!=None else "run mode"})")

  #Init terminal mode, call shell
  Restart=False
  try:
    terminal.SetRawTerminalMode()
    Sh=shell.Shell(Args.Command,Args.SkipInit,Args.InitCommand,Args.InitScript,CommandsFolder,\
             CompletersFolder,WhippetsFolder,HistoryFile,MaxHistoryCommands,NoTruncate)
    Restart=Sh.Run()
  finally:
    terminal.RestoreTerminalMode()
  
  #Signal exit in debug log
  debug.Get().Send(f"{const.APP_NAME} v{Version} terminated ({"command mode: "+Args.Command if Args.Command!=None else "run mode"})")

  #Exit
  return Restart

# ---------------------------------------------------------------------------
# Entry point: parse arguments, initialize subsystems, and run the shell
# Args: None
# Returns: None
# ---------------------------------------------------------------------------
def Main():

  #Main file path
  MainFilePath=sys.modules["__main__"].__file__
  
  #Get version number
  Version=utils.GetVersion(MainFilePath)
  
  #Get command line arguments
  Args,ArgParser=GetCommandLineArgs(Version)
  
  #If no arguments provided,print help and exit
  if Args.Run==False and Args.Command==None and Args.DebugKb==False:
    ArgParser.print_help()
    sys.exit(0)

  #Enter keyboard debugging mode
  if Args.DebugKb==True:
    terminal.SetRawTerminalMode()
    while True:
      Key=terminal.ReadKey()
      print(Key.Code())
      if Key.Code()=="ESCAPE":
        break 
    terminal.RestoreTerminalMode()
    sys.exit(0)

  #Run shell interpreter in a loop to allow for restarts
  while True:
    Restart=StartShell(MainFilePath,Version,Args)
    if Restart==False:
      break

#Entry point
if __name__=="__main__":
  Main()
