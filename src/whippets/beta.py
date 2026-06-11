#Import libraries
import ansi
import const
from pathlib import Path

#Calculate and return whippet
def Whippet(Config):

  #Get colors
  BetaModeColor=Config.get("beta_mode_color",const.DEFAULT_FOREGROUND_COLOR)
  
  #Calculate beta tag
  if Path(__file__).parent.parent.parent.name.lower()=="beta":
    Beta=ansi.SetRgb(BetaModeColor)+" (beta)"+ansi.ResetColor()
  else:
    Beta=""

  #Return value
  return Beta