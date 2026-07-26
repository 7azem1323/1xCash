from telegram.ext import ConversationHandler

# ══════════════════════════════════════════════
# DEPOSIT STATES
# ══════════════════════════════════════════════
DEP_PLATFORM   = 0
DEP_ACCOUNT_ID = 1
DEP_AMOUNT     = 2
DEP_CONFIRM    = 3

# ══════════════════════════════════════════════
# WITHDRAW STATES
# ══════════════════════════════════════════════
WIT_PLATFORM = 10
WIT_AMOUNT   = 11
WIT_CONFIRM  = 12

# ══════════════════════════════════════════════
# SUPPORT STATES
# ══════════════════════════════════════════════
SUP_REASON = 20

# ══════════════════════════════════════════════
# ADMIN STATES
# ══════════════════════════════════════════════
ADM_BROADCAST         = 30
ADM_EDIT_MSG_KEY      = 31
ADM_EDIT_MSG_VAL      = 32
ADM_EDIT_BTN_KEY      = 33
ADM_EDIT_BTN_VAL      = 34
ADM_ADD_ADMIN         = 35
ADM_REMOVE_ADMIN      = 36
ADM_REJECT_REASON     = 37
ADM_ADD_CUSTOM_LABEL  = 38
ADM_ADD_CUSTOM_URL    = 39
ADM_EDIT_SETTING_KEY  = 40
ADM_EDIT_SETTING_VAL  = 41
