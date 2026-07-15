"""Semantic UI Bridge —— 自定义异常"""


class SUBError(Exception):
    """Bridge 基础异常"""


class SUBTimeoutError(SUBError):
    """等待超时"""


class AdapterError(SUBError):
    """适配器底层错误"""


class ElementNotFoundError(SUBError):
    """元素未找到"""


class ActionError(SUBError):
    """动作执行失败"""
