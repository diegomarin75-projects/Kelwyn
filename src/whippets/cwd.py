#Import libraries
import os
import utils

#Calculate and return whippet
def Whippet(Config):
  Cwd=os.getcwd()
  Cwd=utils.FilePathIntr2Disp(Cwd,Config)
  return Cwd
