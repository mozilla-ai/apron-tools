"""Microsoft provider.

API docs:
  - Excel: https://learn.microsoft.com/en-us/graph/api/resources/excel
  - Outlook: https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview
  - PowerPoint: https://learn.microsoft.com/en-us/graph/api/resources/presentation
  - SharePoint: https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
  - Teams: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

from .excel import (
    microsoft_excel_add_worksheet,
    microsoft_excel_append_row,
    microsoft_excel_create_workbook,
    microsoft_excel_get_workbook_info,
    microsoft_excel_list_workbooks,
    microsoft_excel_read_worksheet,
    microsoft_excel_update_worksheet,
)
from .outlook import (
    microsoft_outlook_create_draft,
    microsoft_outlook_list_emails,
    microsoft_outlook_read_email,
    microsoft_outlook_send_draft,
    microsoft_outlook_send_email,
)
from .sharepoint import (
    microsoft_sharepoint_create_folder,
    microsoft_sharepoint_explore_drive,
    microsoft_sharepoint_list_drives,
    microsoft_sharepoint_list_sites,
    microsoft_sharepoint_move_file,
    microsoft_sharepoint_search,
)
from .teams import (
    microsoft_teams_explore_workspace,
    microsoft_teams_get_channel_info,
    microsoft_teams_list_chats,
    microsoft_teams_read_channel_messages,
    microsoft_teams_read_chat_messages,
    microsoft_teams_read_message_replies,
    microsoft_teams_send_channel_message,
    microsoft_teams_send_chat_message,
)

__all__ = [
    "microsoft_excel_add_worksheet",
    "microsoft_excel_append_row",
    "microsoft_excel_create_workbook",
    "microsoft_excel_get_workbook_info",
    "microsoft_excel_list_workbooks",
    "microsoft_excel_read_worksheet",
    "microsoft_excel_update_worksheet",
    "microsoft_outlook_create_draft",
    "microsoft_outlook_list_emails",
    "microsoft_outlook_read_email",
    "microsoft_outlook_send_draft",
    "microsoft_outlook_send_email",
    "microsoft_sharepoint_create_folder",
    "microsoft_sharepoint_explore_drive",
    "microsoft_sharepoint_list_drives",
    "microsoft_sharepoint_list_sites",
    "microsoft_sharepoint_move_file",
    "microsoft_sharepoint_search",
    "microsoft_teams_explore_workspace",
    "microsoft_teams_get_channel_info",
    "microsoft_teams_list_chats",
    "microsoft_teams_read_channel_messages",
    "microsoft_teams_read_chat_messages",
    "microsoft_teams_read_message_replies",
    "microsoft_teams_send_channel_message",
    "microsoft_teams_send_chat_message",
]

try:
    from .powerpoint import (
        microsoft_powerpoint_add_slide,
        microsoft_powerpoint_create_presentation,
        microsoft_powerpoint_explore_presentations,
        microsoft_powerpoint_read_presentation,
        microsoft_powerpoint_update_slide_text,
        microsoft_powerpoint_upload_to_onedrive,
    )

    __all__ += [
        "microsoft_powerpoint_add_slide",
        "microsoft_powerpoint_create_presentation",
        "microsoft_powerpoint_explore_presentations",
        "microsoft_powerpoint_read_presentation",
        "microsoft_powerpoint_update_slide_text",
        "microsoft_powerpoint_upload_to_onedrive",
    ]
except ImportError:
    import logging as _logging

    _logging.getLogger(__name__).debug(
        "PowerPoint tools unavailable — install apron-tools[powerpoint] for python-pptx support."
    )

try:
    from .word import (
        microsoft_word_create_document,
        microsoft_word_explore_documents,
        microsoft_word_read_document,
        microsoft_word_update_document,
        microsoft_word_upload_to_onedrive,
    )

    __all__ += [
        "microsoft_word_create_document",
        "microsoft_word_explore_documents",
        "microsoft_word_read_document",
        "microsoft_word_update_document",
        "microsoft_word_upload_to_onedrive",
    ]
except ImportError:
    import logging as _logging

    _logging.getLogger(__name__).debug("Word tools unavailable — install apron-tools[word] for python-docx support.")
