#Import libraries
import os
import platform

#Calculate and return whippet
def Whippet(Config):
  Cwd=os.getcwd()
  if (platform.system()=="Windows" and Cwd.upper().startswith(Config["kelwyn_home"].upper())) \
  or Cwd.startswith(Config["kelwyn_home"]):
    Cwd="~"+Cwd[len(Config["kelwyn_home"]):]
  return Cwd
