# -*- coding: utf-8 -*-
"""浏览器 UI 自动化基础设施（Selenium + Chrome）。

环境约束说明：本机 Chrome 128 与缓存的 chromedriver 128 大版本一致，
通过显式 binary_location / service 路径启动，避免离线环境下的驱动下载。
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .paths import ACCOUNTS, SCREENSHOT_DIR, WEB_URL

CHROME_CANDIDATES = [
    os.getenv("CHROME_BINARY", ""),
    r"C:\Users\86198\AppData\Local\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

DRIVER_CANDIDATES = [
    os.getenv("CHROMEDRIVER", ""),
    r"C:\Users\86198\.wdm\drivers\chromedriver\win64\128.0.6613.137\chromedriver-win32\chromedriver.exe",
]


def _first_existing(candidates: list[str]) -> str | None:
    for item in candidates:
        if item and Path(item).exists():
            return item
    return None


def find_chromedriver() -> str | None:
    found = _first_existing(DRIVER_CANDIDATES)
    if found:
        return found
    cache = Path.home() / ".wdm" / "drivers" / "chromedriver"
    if cache.exists():
        for path in sorted(cache.rglob("chromedriver.exe")):
            return str(path)
    return None


def build_driver(headless: bool = True) -> webdriver.Chrome:
    binary = _first_existing(CHROME_CANDIDATES)
    if binary is None:
        raise RuntimeError("未找到可用的 Chrome/Edge 浏览器可执行文件")
    options = Options()
    options.binary_location = binary
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    driver_path = find_chromedriver()
    driver = webdriver.Chrome(service=Service(driver_path), options=options)
    driver.set_page_load_timeout(45)
    return driver


class Page:
    """页面对象基类：只放两个模块都会用到的通用动作。"""

    def __init__(self, driver: webdriver.Chrome, timeout: int = 20) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    # ------------------------------------------------------------ 基础动作
    def open(self, path: str) -> None:
        self.driver.get(f"{WEB_URL}{path}")
        self.wait_document_ready()

    def wait_document_ready(self) -> None:
        self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    def wait_visible(self, by: str, selector: str):
        return self.wait.until(EC.visibility_of_element_located((by, selector)))

    def wait_clickable(self, by: str, selector: str):
        return self.wait.until(EC.element_to_be_clickable((by, selector)))

    def wait_presence(self, by: str, selector: str):
        return self.wait.until(EC.presence_of_element_located((by, selector)))

    def texts(self, by: str, selector: str) -> list[str]:
        return [el.text.strip() for el in self.driver.find_elements(by, selector)]

    def screenshot(self, name: str) -> str:
        path = SCREENSHOT_DIR / f"{name}.png"
        self.driver.save_screenshot(str(path))
        return str(path)

    def toast_text(self, timeout: float = 4.0) -> str:
        """Element Plus 的消息提示文本；无提示返回空串。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            els = self.driver.find_elements(By.CSS_SELECTOR, ".el-message")
            for el in els:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()
            time.sleep(0.2)
        return ""

    def close_dialogs(self) -> None:
        for el in self.driver.find_elements(By.CSS_SELECTOR, ".el-dialog__headerbtn"):
            if el.is_displayed():
                el.click()
                time.sleep(0.3)


class LoginPage(Page):
    def login(self, account: str) -> None:
        cred = ACCOUNTS[account]
        self.open("/login")
        self.wait_visible(By.CSS_SELECTOR, "input[placeholder='请输入用户名']").send_keys(cred["username"])
        self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='请输入密码']").send_keys(cred["password"])
        self.wait_clickable(By.CSS_SELECTOR, "button.login-btn").click()
        self.wait.until(lambda d: "/login" not in d.current_url)
        self.wait_document_ready()

def ui_login(driver: webdriver.Chrome, account: str) -> None:
    LoginPage(driver).login(account)
