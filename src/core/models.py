"""Semantic UI Bridge —— 数据模型（最小可用版）"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class UIRole(str, Enum):
    BUTTON = "button"
    TEXTBOX = "textbox"
    TEXT = "text"
    CHECKBOX = "checkbox"
    SELECT = "select"
    SLIDER = "slider"
    IMAGE = "image"
    TABLE = "table"
    DIALOG = "dialog"
    GROUP = "group"


class UIElement(BaseModel):
    id: str
    role: UIRole
    label: str | None = None
    states: list[str] = []
    value: str | None = None
    actions: list[str] = []
    children: list[UIElement] = []
    bounds: dict[str, float] | None = None
    platform_data: dict[str, Any] | None = None


class UITree(BaseModel):
    app_name: str
    app_title: str
    root: UIElement
    timestamp: float = 0.0
    focused_element_id: str | None = None


class Action(BaseModel):
    action: str
    target: str
    params: dict[str, Any] = {}


class ActionResult(BaseModel):
    success: bool
    action: Action
    result_tree: UITree | None = None
    diff: list[str] = []
    error: str | None = None
