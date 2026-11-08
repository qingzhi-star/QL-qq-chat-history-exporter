"""读取账号的本机显示资料，供桌面内核与账号面板共用。"""
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3

from qqexport.core import companions, keystore
from qqexport.qq import avatars, contacts


@dataclass(frozen=True)
class Identity:
    uin: str
    name: str = "QQ 用户"
    avatar: bytes | None = None
    active: bool = False


def profile_name(book, uin):
    person = book.friends_by_uin.get(uin)
    if person and (person.nick or person.remark):
        return person.nick or person.remark
    for (_, member_uin), member in book.members_by_uin.items():
        if member_uin == uin and member.nick:
            return member.nick
    return "QQ 用户"


def database_in_use(account):
    """只探测文件共享占用，不读取认证资料。"""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(account.msg_db), 0x80000000, 0, None, 3, 128, None)
    if handle == ctypes.c_void_p(-1).value:
        return ctypes.get_last_error() in (32, 33)
    kernel.CloseHandle(handle)
    return False


def read_identity(account, *, include_avatar=True):
    name = "QQ 用户"
    try:
        key = keystore.KeyStore().load(account.uin)
        if key:
            from qqexport.temporary import workspace
            with workspace("profiles") as temp:
                profile = companions.decrypt_companion(account.db_dir / "profile_info.db", key, Path(temp))
                book = contacts.Contacts.load(profile, None, account_uin=account.uin)
                name = profile_name(book, account.uin)
                if name == "QQ 用户":
                    group = companions.decrypt_companion(account.db_dir / "group_info.db", key, Path(temp))
                    book = contacts.Contacts.load(profile, group, account_uin=account.uin)
                    name = profile_name(book, account.uin)
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        pass
    avatar = avatars.fetch_avatar(account.uin) if include_avatar else None
    return Identity(account.uin, name, avatar, database_in_use(account))
