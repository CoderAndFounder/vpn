from aiogram.fsm.state import State, StatesGroup

class TransferState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_recipient = State() 