# ---------------------------------------------------------------------------------------------------------------------
# const.py: Constant definitions
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import ansi

# ---------------------------------------------------------------------------------------------------------------------
# General constants
# ---------------------------------------------------------------------------------------------------------------------

#Application name
APP_NAME="kelwyn"

# Application banner 1
BANNER1_COLOR1="#009000"
BANNER1_COLOR2="#106410"
BANNER1_COLOR3="#404040"
ASCII_BANNER1=rf"""
██╗ ██╗████╗██╗   ██╗    ██╗██╗   ██╗███╗  ██╗
████╔╝ ██╗  ██║   ██║ █╗ ██║ ╚████╔╝ ██╔██╗██║
██║ ██╗████╗█████╗╚███╔███╔╝   ██║   ██║ ╚███║
╚═╝ ╚═╝╚═══╝╚════╝ ╚══╝╚══╝    ╚═╝   ╚═╝  ╚══╝  (v<version>)
""" \
.replace("█",ansi.SetFgColor(BANNER1_COLOR1)+"█"+ansi.ResetColor()) \
.replace("╗",ansi.SetFgColor(BANNER1_COLOR2)+"╗"+ansi.ResetColor()) \
.replace("╔",ansi.SetFgColor(BANNER1_COLOR2)+"╔"+ansi.ResetColor()) \
.replace("╚",ansi.SetFgColor(BANNER1_COLOR2)+"╚"+ansi.ResetColor()) \
.replace("║",ansi.SetFgColor(BANNER1_COLOR2)+"║"+ansi.ResetColor()) \
.replace("╝",ansi.SetFgColor(BANNER1_COLOR3)+"╝"+ansi.ResetColor()) \
.replace("═",ansi.SetFgColor(BANNER1_COLOR3)+"═"+ansi.ResetColor())

# Application banner 1
BANNER2_COLOR1="#5555FF"
BANNER2_COLOR2="#0000FF"
ASCII_BANNER2=rf"""
 █████               ████                                       
░░███               ░░███                                       
 ░███ █████  ██████  ░███  █████ ███ █████ █████ ████ ████████  
 ░███░░███  ███░░███ ░███ ░░███ ░███░░███ ░░███ ░███ ░░███░░███ 
 ░██████░  ░███████  ░███  ░███ ░███ ░███  ░███ ░███  ░███ ░███ 
 ░███░░███ ░███░░░   ░███  ░░███████████   ░███ ░███  ░███ ░███ 
 ████ █████░░██████  █████  ░░████░████    ░░███████  ████ █████
░░░░ ░░░░░  ░░░░░░  ░░░░░    ░░░░ ░░░░      ░░░░░███ ░░░░ ░░░░░   (v<version>)
                                            ███ ░███            
                                           ░░██████             
                                            ░░░░░░              
""" \
.replace("█",ansi.SetFgColor(BANNER2_COLOR1)+"█"+ansi.ResetColor()) \
.replace("░",ansi.SetFgColor(BANNER2_COLOR2)+"░"+ansi.ResetColor())

# Wellcome lines
WELCOME_LINES=[
  "Welcome to {app} shell — python-integrated command line interpreter".format(app=APP_NAME),
  "Type 'help' for available commands,'exit' to quit.",
  "",
]

#Default prompt string
DEFAULT_PROMPT="{%94m%}[<month>/<day>·<hour><min><sec>]{%0m%}<beta> {%92m%}<cwd>{%0m%}<git> {%90m%}>{%0m%} "

#Config file environment variable and default value
CONFIG_VAR_NAME="KELWYN_CONFIG_FILE"
CONFIG_FILE="kelwyn-cfg.json"

#History file environment variable and default value
HISTORY_VAR_NAME="KELWYN_HISTORY_FILE"
HISTORY_FILE=".kelwyn_history"
MAX_HISTORY_COMMANDS=25000

#Debug log environment variable and default value
DEBUG_LOG_VAR_NAME="KELWYN_DEBUG_LOG"
DEBUG_LOG_FILE=".kelwyn_debug.log"
MAX_DEBUG_LINES=5000

#Default option box maximun height percent
DEFAULT_BOX_MAX_HEIGHT_PERCENT=30

#Default colors
DEFAULT_FOREGROUND_COLOR="dark_white"
DEFAULT_BACKGROUND_COLOR="dark_black"
DEFAULT_OPT_ERROR_COLOR="bright_red"

#Git info timeout (in seconds)
DEFAULT_GIT_INFO_TIMEOUT_SECS=5