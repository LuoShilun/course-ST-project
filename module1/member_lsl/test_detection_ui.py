# -*- coding: utf-8 -*-
"""模块一：检测模块浏览器 UI 自动化用例（TC-DET-17）。

被测页面：/detect 智能检测工作台。
本用例通过真实浏览器登录、加载页面并读取"水域场景适配模型"下拉框的
渲染结果，验证页面默认选中项与接口返回的模型列表是否一致。
"""
from __future__ import annotations

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from common.ui import Page

pytestmark = [pytest.mark.ui]


def _open_models_dropdown(page: Page) -> list[str]:
    """展开模型下拉框并读取全部选项文案。"""
    select = page.wait_clickable(By.CSS_SELECTOR, ".config-card .el-select__wrapper")
    select.click()
    time.sleep(1.2)
    options = page.driver.find_elements(By.CSS_SELECTOR, ".el-select-dropdown__item")
    labels = [el.text.strip() for el in options if el.text.strip()]
    page.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    time.sleep(0.5)
    return labels


def _selected_text(page: Page) -> str:
    for selector in (".config-card .el-select__selected-item", ".config-card .el-select__placeholder"):
        els = page.driver.find_elements(By.CSS_SELECTOR, selector)
        for el in els:
            if el.is_displayed() and el.text.strip():
                return el.text.strip()
    return ""


@pytest.mark.case("TC-DET-17")
@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="BUG-06：默认 model_key 为 mock-default，不在选项列表中，下拉框显示为空")
def test_model_select_default_value(ui_user1, actual):
    page = Page(ui_user1)
    page.open("/detect")
    page.wait_visible(By.CSS_SELECTOR, ".config-card .el-select__wrapper")

    labels = _open_models_dropdown(page)
    selected = _selected_text(page)
    hint = ""
    hints = ui_user1.find_elements(By.CSS_SELECTOR, ".config-card .form-hint")
    if hints:
        hint = hints[0].text.strip()
    page.screenshot("TC-DET-17-model-select")

    actual(f"下拉框选项 {len(labels)} 个：{'、'.join(labels)}；默认选中项显示为“{selected or '(空)'}”；"
           f"引擎档案提示：{hint or '(空)'}")
    assert labels, "模型下拉框没有任何选项"
    assert selected, "模型下拉框默认没有选中任何选项（页面显示占位符）"
    assert selected in labels, f"默认选中项 {selected!r} 不在选项列表中 {labels}"
