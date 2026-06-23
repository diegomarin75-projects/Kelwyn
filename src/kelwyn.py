#Import libraries
import os
import sys
import argparse
import ansi
import const
import debug
import terminal
import shell
import utils
from pathlib import Path

# ---------------------------------------------------------------------------
# Entry point: parse arguments, initialize subsystems, and run the shell
# Args: None
# Returns: None
# ---------------------------------------------------------------------------
def Main():

  #Set up argument parser
  ArgParser=argparse.ArgumentParser(description=f"{const.APP_NAME} - A cross-platform command-line shell interpreter",add_help=True)
  RunGroup=ArgParser.add_mutually_exclusive_group()
  RunGroup.add_argument("--run",dest="Run",action="store_true",help="Start the shell",default=False)
  RunGroup.add_argument("--command",dest="Command",type=str,metavar="CMD",help="Execute a command and exit",default=None)
  ArgParser.add_argument("--config",dest="ConfigFile",type=str,metavar="PATH",help="Path to config file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--history",dest="HistoryFile",type=str,metavar="PATH",help="Path to history file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--debug-log",dest="DebugLogFile",type=str,metavar="PATH",help="Path to debug log file (default: same directory as python script)",default=None)
  ArgParser.add_argument("--skip-init",dest="SkipInit",action="store_true",help="Skip the init script (use with --run or --command)",default=False)
  ArgParser.add_argument("--init-command",dest="InitCommand",type=str,metavar="CMD",help="Command to execute at startup (use with --run)",default=None)
  ArgParser.add_argument("--init-script",dest="InitScript",type=str,metavar="PATH",help="Path to init script to execute at startup (use with --run)",default=None)
  Args=ArgParser.parse_args()
  
  #If no arguments provided,print help and exit
  if Args.Run==False and Args.Command==None:
    ArgParser.print_help()
    sys.exit(0)

  #Get config file
  if Args.ConfigFile!=None:
    ConfigFile=Args.ConfigFile
  elif const.CONFIG_VAR_NAME in os.environ:
    ConfigFile=os.environ[const.CONFIG_VAR_NAME]
  else:
    ConfigFile=Path(os.path.dirname(os.path.abspath(__file__))).parent / "cfg" / const.CONFIG_FILE

  #Load config file
  Status,Message,Config=utils.JsonFileParser(ConfigFile)
  if Status==False:
    print("Error loading config file: "+Message)
    sys.exit(1)
  Config["config_file_path"]=ConfigFile
  
  #Get history file
  if Args.HistoryFile!=None:
    HistoryFile=Args.HistoryFile
  elif "history_file" in Config:
    HistoryFile=Config["history_file"]
  elif const.HISTORY_VAR_NAME in os.environ:
    HistoryFile=os.environ[const.HISTORY_VAR_NAME]  
  else:
    HistoryFile=Path(os.path.dirname(os.path.abspath(__file__))).parent / const.HISTORY_FILE
  
  #Get debug log file
  if Args.DebugLogFile!=None:
    DebugLogFile=Args.DebugLogFile
  elif "debug_log_file" in Config:
    DebugLogFile=Config["debug_log_file"]
  if const.DEBUG_LOG_VAR_NAME in os.environ:
    DebugLogFile=os.environ[const.DEBUG_LOG_VAR_NAME]
  else:
    DebugLogFile=Path(os.path.dirname(os.path.abspath(__file__))).parent / const.DEBUG_LOG_FILE
  
  #Setup other configuration variables
  CommandsFolder=os.path.join(os.path.dirname(__file__),"commands")
  CompletersFolder=os.path.join(os.path.dirname(__file__),"completers")
  WhippetsFolder=os.path.join(os.path.dirname(__file__),"whippets")
  MaxDebugLines=Config.get("max_debug_lines",const.MAX_DEBUG_LINES)
  MaxHistoryCommands=Config.get("max_history_commands",const.MAX_HISTORY_COMMANDS)

  #If executed for single command avoid truncation (debug log and history)
  NoTruncate=(True if Args.Command!=None else False)
  
  #Initialize debug log
  debug.Init(DebugLogFile,MaxDebugLines,NoTruncate,Config)

  #Signal start in debug log
  debug.Get().Send(f"{const.APP_NAME} v{const.VERSION} started ({"command mode: "+Args.Command if Args.Command!=None else "run mode"})")

  #Init terminal mode, call shell
  try:
    terminal.SetRawTerminalMode()
    Sh=shell.Shell(Args.Command,Args.SkipInit,Args.InitCommand,Args.InitScript,const.VERSION,CommandsFolder,\
                   CompletersFolder,WhippetsFolder,HistoryFile,MaxHistoryCommands,NoTruncate,Config)
    Sh.Run()
  finally:
    terminal.RestoreTerminalMode()
  
  #Signal exit in debug log
  debug.Get().Send(f"{const.APP_NAME} v{const.VERSION} terminated ({"command mode: "+Args.Command if Args.Command!=None else "run mode"})")

#Entry point
if __name__=="__main__":
  Main()
