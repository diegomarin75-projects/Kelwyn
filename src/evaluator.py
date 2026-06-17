# ---------------------------------------------------------------------------------------------------------------------
# evaluation.py - Evaluatino of expressions for eval() built-in function in command execution
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import debug
import math
import cmath
import random

# ---------------------------------------------------------------------------------------------------------------------
# Expression evaluator class
# ---------------------------------------------------------------------------------------------------------------------
class Evaluator:
  
  #Constructor class
  def __init__(self,Config):
    self.Config=Config
  
  #Evaluate expression with limited built-ins and math, cmath, random modules
  def Evaluate(self,Expression):
    try:
      debug.Get().Send(f"evaluator input: Expression='{Expression}'")
      Globals={"__builtins__":{},"math":math,"cmath":cmath,"random":random}
      Result=str(eval(Expression,Globals))
      debug.Get().Send(f"evaluator output: Result='{Result}'")
    except Exception as Ex:
      Message=f"Error evaluating expression '{Expression}': {Ex}"
      return False,Message,None
    return True,"",Result
