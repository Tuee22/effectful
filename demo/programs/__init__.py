"""Pure logic effect programs for demo app."""

from demo.programs.auth_programs import (
    login_program,
    logout_program,
    refresh_program,
    register_program,
)
from demo.programs.chat_programs import send_authenticated_message_with_storage_program
from demo.programs.message_programs import get_message_program, send_message_program
from demo.programs.user_programs import (
    delete_user_program,
    get_user_program,
    list_users_program,
    update_user_program,
)

__all__ = [
    # Auth programs
    "login_program",
    "logout_program",
    "refresh_program",
    "register_program",
    # User programs
    "get_user_program",
    "list_users_program",
    "update_user_program",
    "delete_user_program",
    # Message programs
    "send_message_program",
    "get_message_program",
    # Chat programs (complex, all 6 infrastructure types)
    "send_authenticated_message_with_storage_program",
]
