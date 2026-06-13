#Import libraries
import terminal

#Calculate and return whippet
def Whippet(Config):
  _,Cols=TerminalSize=terminal.GetTerminalSize()
  return "─"*(Cols-1)
