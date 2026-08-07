"""Functional and responsive QA for the static academic website."""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = ""
QA_DIR = Path(os.environ.get("QA_DIRECTORY", PROJECT_ROOT / "_local_docs" / "qa"))
SITE_DIRECTORY = Path(os.environ.get("SITE_DIRECTORY", PROJECT_ROOT / "site"))


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve the static site without noisy access logs during QA."""

    def log_message(self, format, *args):  # noqa: A003 - inherited API name
        return


@contextmanager
def local_site_server():
    """Run the website from an ephemeral localhost port."""
    global BASE_URL
    handler = partial(QuietHandler, directory=str(SITE_DIRECTORY.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    BASE_URL = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def navigate(page) -> None:
    """Open the local page with a short retry for Windows startup races."""
    last_error = None
    for _ in range(3):
        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
            return
        except Exception as error:  # Playwright sync errors share this path.
            last_error = error
            page.wait_for_timeout(500)
    raise last_error


def reset_for_capture(page) -> None:
    """Reload at the top before making viewport and full-page screenshots."""
    navigate(page)
    page.evaluate(
        """() => {
          document.documentElement.style.scrollBehavior = 'auto';
          window.scrollTo(0, 0);
        }"""
    )
    page.wait_for_timeout(100)


def assert_no_horizontal_overflow(page, label: str) -> None:
    sizes = page.evaluate(
        """() => ({
          viewport: document.documentElement.clientWidth,
          scroll: document.documentElement.scrollWidth
        })"""
    )
    if sizes["scroll"] <= sizes["viewport"] + 1:
        return
    offenders = page.evaluate(
        """() => [...document.querySelectorAll('*')]
          .map((element) => {
            const box = element.getBoundingClientRect();
            return {tag: element.tagName, className: element.className, left: box.left, right: box.right, width: box.width};
          })
          .filter((item) => item.left < -1 || item.right > document.documentElement.clientWidth + 1)
          .sort((a, b) => b.right - a.right)
          .slice(0, 12)"""
    )
    raise AssertionError(f"{label}: horizontal overflow {sizes}; offenders={offenders}")


def assert_publication_image_ratio(page, label: str) -> None:
    """Ensure each publication image keeps its own source aspect ratio."""
    boxes = page.locator(".publication-image img").evaluate_all(
        """elements => elements.map(element => {
          const box = element.getBoundingClientRect();
          return {
            width: box.width,
            height: box.height,
            naturalWidth: element.naturalWidth,
            naturalHeight: element.naturalHeight
          };
        })"""
    )
    assert len(boxes) == 2, f"{label}: expected two publication images"
    for box in boxes:
        ratio = box["width"] / box["height"]
        source_ratio = box["naturalWidth"] / box["naturalHeight"]
        assert abs(ratio - source_ratio) < 0.03, (
            f"{label}: rendered ratio {ratio:.3f} differs from source ratio {source_ratio:.3f}"
        )


def run() -> None:
    QA_DIR.mkdir(exist_ok=True)
    problems: list[str] = []
    broken_resources: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        desktop = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        desktop.on(
            "console",
            lambda message: problems.append(f"console {message.type}: {message.text}")
            if message.type == "error"
            else None,
        )
        desktop.on("pageerror", lambda error: problems.append(f"page error: {error}"))
        desktop.on(
            "response",
            lambda response: broken_resources.append(f"{response.status} {response.url}")
            if response.status >= 400 and response.url.startswith(BASE_URL)
            else None,
        )
        navigate(desktop)

        assert desktop.title() == "Zebin Zhang"
        assert desktop.locator("#about-title").inner_text() == "Zebin Zhang"
        assert desktop.locator("#publications article.publication-entry").count() == 2
        assert desktop.locator("img:not([alt]), img[alt='']").count() == 0
        assert desktop.locator("main h1").count() == 4
        assert desktop.locator("main h2").count() == 3
        assert desktop.locator(".site-nav a[href='#news']").count() == 1
        assert desktop.locator("#honors .honors-list li").count() == 3
        assert desktop.locator("#research-title + .research-list li").count() == 3
        assert desktop.locator("#research-title + .research-list li > span").count() == 3
        assert desktop.locator("#research-title + .research-list strong").count() == 6
        assert desktop.locator("#about .about-copy a[href='https://ic.pku.edu.cn/']").count() == 1
        assert desktop.locator("#news time[datetime='2021-09']").count() == 1
        assert desktop.locator("#news a[href='https://eecs.pku.edu.cn/']").count() == 1
        assert "SNW" in desktop.locator("#news .news-list li").nth(0).inner_text()
        assert "EDTM" in desktop.locator("#news .news-list li").nth(1).inner_text()
        assert "(co-first author)" in desktop.locator("#news .news-list li").nth(0).inner_text()
        assert "(first author)" in desktop.locator("#news .news-list li").nth(1).inner_text()
        assert desktop.locator("#news .news-list li").nth(0).locator("strong").inner_text() == "IEEE SNW 2026"
        assert desktop.locator("#news .news-list li").nth(1).locator("a strong").inner_text() == "IEEE EDTM 2026"
        assert "Graduated from Peking University" in desktop.locator("#news .news-list li").nth(2).inner_text()
        assert "started Ph.D. study" in desktop.locator("#news .news-list li").nth(2).inner_text()
        assert desktop.locator("#news time").all_inner_texts() == ["Jun 2026", "Mar 2026", "Sep 2025", "Sep 2021"]
        assert desktop.locator(
            "#news a[href='https://ieeexplore.ieee.org/abstract/document/11497247']"
        ).count() == 1
        assert desktop.locator(
            "a[href='https://ieeexplore.ieee.org/abstract/document/11497247']"
        ).count() == 3
        assert desktop.locator(".publication-entry:nth-of-type(2) .publication-links").count() == 0
        assert desktop.locator("img[src='assets/img/snw2026-slide11.png']").count() == 1
        assert desktop.locator("img[src='assets/img/zebin-zhang-id.jpg']").count() == 1
        assert_no_horizontal_overflow(desktop, "desktop")
        assert_publication_image_ratio(desktop, "desktop")

        publication_widths = desktop.locator(".publication-image img").evaluate_all(
            "elements => elements.map(element => element.getBoundingClientRect().width)"
        )
        assert all(width >= 378 for width in publication_widths), publication_widths

        body_font = desktop.locator("body").evaluate("element => getComputedStyle(element).fontFamily")
        title_font = desktop.locator("main h1").first.evaluate("element => getComputedStyle(element).fontFamily")
        assert "Calibri" in body_font, body_font
        assert "Georgia" in title_font or "Times New Roman" in title_font, title_font
        assert float(desktop.locator("body").evaluate("element => getComputedStyle(element).fontSize").removesuffix("px")) >= 24
        assert float(desktop.locator("main h1").first.evaluate("element => getComputedStyle(element).fontSize").removesuffix("px")) >= 42
        assert float(desktop.locator(".publication-text h2").first.evaluate("element => getComputedStyle(element).fontSize").removesuffix("px")) >= 23

        honors_year = desktop.locator("#honors time").last.evaluate(
            """element => ({
              text: element.textContent,
              whiteSpace: getComputedStyle(element).whiteSpace,
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth
            })"""
        )
        assert honors_year["text"] == "2023"
        assert honors_year["whiteSpace"] == "nowrap"
        assert honors_year["scrollWidth"] <= honors_year["clientWidth"] + 1, honors_year

        news_times = desktop.locator("#news time").evaluate_all(
            """elements => elements.map(element => ({
              text: element.textContent,
              whiteSpace: getComputedStyle(element).whiteSpace,
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth
            }))"""
        )
        assert all(item["whiteSpace"] == "nowrap" for item in news_times), news_times
        assert all(item["scrollWidth"] <= item["clientWidth"] + 1 for item in news_times), news_times

        desktop_portrait = desktop.locator(".profile-card img").bounding_box()
        assert desktop_portrait
        assert desktop_portrait["width"] <= 171 and desktop_portrait["height"] <= 249

        reset_for_capture(desktop)
        desktop.screenshot(path=str(QA_DIR / "desktop-viewport.png"))
        desktop.screenshot(path=str(QA_DIR / "desktop.png"), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.on(
            "console",
            lambda message: problems.append(f"mobile console {message.type}: {message.text}")
            if message.type == "error"
            else None,
        )
        mobile.on("pageerror", lambda error: problems.append(f"mobile page error: {error}"))
        navigate(mobile)

        assert_no_horizontal_overflow(mobile, "mobile")
        assert_publication_image_ratio(mobile, "mobile")
        mobile_portrait = mobile.locator(".profile-card img").bounding_box()
        assert mobile_portrait
        assert mobile_portrait["width"] <= 151 and mobile_portrait["height"] <= 220

        menu = mobile.locator(".menu-toggle")
        assert menu.is_visible()
        menu.click()
        assert menu.get_attribute("aria-expanded") == "true"
        assert mobile.locator(".site-nav").is_visible()
        mobile.locator(".site-nav a[href='#news']").click()
        mobile.wait_for_timeout(200)
        assert menu.get_attribute("aria-expanded") == "false"
        assert not mobile.locator(".site-nav").is_visible()
        assert "#news" in mobile.url

        reset_for_capture(mobile)
        mobile.screenshot(path=str(QA_DIR / "mobile-viewport.png"))
        mobile.screenshot(path=str(QA_DIR / "mobile.png"), full_page=True)
        browser.close()

    assert not problems, "\n".join(problems)
    assert not broken_resources, "\n".join(broken_resources)
    print(
        "PASS: concise desktop/mobile layout, News navigation, Honors content, Calibri/serif typography, "
        "portrait sizing, natural publication image ratios, IEEE link, assets, and console checks"
    )


if __name__ == "__main__":
    with local_site_server():
        run()
