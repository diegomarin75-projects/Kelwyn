#Import libraries
import ansi
import const
import utils

#Calculate and return whippet
def Whippet(Config):

  #Get colors
  GitCleanColor=Config.get("git_clean_color",const.DEFAULT_FOREGROUND_COLOR)
  GitDirtyColor=Config.get("git_dirty_color",const.DEFAULT_FOREGROUND_COLOR)
  GitConflictColor=Config.get("git_conflict_color",const.DEFAULT_FOREGROUND_COLOR)
  GitInfoTimeoutSecs=Config.get("git_info_timeout_secs",const.DEFAULT_GIT_INFO_TIMEOUT_SECS)

  #Get git information (failure means not inside a git repo / Cancel / Timeout)
  RetCode,Output=utils.Exec("git status --porcelain=v1 --branch --ahead-behind --untracked-files=all",Timeout=GitInfoTimeoutSecs)
  if RetCode==-1:
    " "+ansi.SetFgColor(GitConflictColor)+"(cancel)"+ansi.ResetColor()
  elif RetCode==-2:
    " "+ansi.SetFgColor(GitConflictColor)+"(timeout)"+ansi.ResetColor()
  elif RetCode != 0:
    return ""

  #Init git information
  Branch=""
  Modified=0
  HasConflict=False
  Ahead=0
  Behind=0

  #Process git output
  for Line in Output.splitlines():

    #Header line with branch information (## main...origin/main [ahead 2, behind 1])
    if Line.startswith("## "):
      BranchInfo=Line[3:]
      Branch=BranchInfo.split("...")[0]
      if "[" in BranchInfo:
        Sync=BranchInfo.split("[",1)[1].rstrip("]")
        for Item in Sync.split(","):
          Item=Item.strip()
          if Item.startswith("ahead "):
            Ahead=Item[6:].strip()
          elif Item.startswith("behind "):
            Behind=Item[7:].strip()

    #File line (XY status codes: UU, AU, UA, DU, UD are conflict states)
    else:
      if Line.strip():
        Modified+=1
        if len(Line)>=2 and "U" in Line[:2]:
          HasConflict=True

  #Exit if branch was not found
  if len(Branch)==0:
    return ""

  #Compose git info
  Info=Branch
  if Modified:
    Info+=":"+str(Modified)+"*"
  if Behind:
    Info+=":"+Behind+"<<"
  if Ahead:
    Info+=":"+Ahead+">>"
  Info="("+Info+")"

  #Set color based on status
  if HasConflict:
    Color=GitConflictColor
  elif Modified:
    Color=GitDirtyColor
  else:
    Color=GitCleanColor

  #Return information
  return " "+ansi.SetFgColor(Color)+Info+ansi.ResetColor()