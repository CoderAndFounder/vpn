from aiogram.fsm.state import State, StatesGroup

class RaffleState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

class AdminUserBalanceState(StatesGroup):
    waiting_for_user_input = State()

class AdminBalanceState(StatesGroup):
    waiting_for_reset_reason = State()

class AdminStates(StatesGroup):
    pass

class ReferralStates(StatesGroup):
    ADD_NAME = State()
    ADD_DESCRIPTION = State()
    ADD_INVITATIONS = State()
    ADD_REWARD = State()
    
    EDIT_SELECT = State()
    EDIT_FIELD = State()
    EDIT_VALUE = State()
    
    DELETE_CONFIRM = State() 