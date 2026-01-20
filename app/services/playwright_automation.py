"""Playwright automation for Google Maps saved places removal."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config import settings
from app.core.exceptions import AuthenticationExpired, AuthenticationRequired, PlaywrightError
from app.models.place import PlaceRemovalResult
from app.models.session import AuthStatus


class PlaywrightAutomation:
    """Automation for Google Maps using Playwright."""

    AUTH_STATE_FILE = "state.json"
    AUTH_VALIDITY_DAYS = 7  # Auth state typically valid for about a week

    def __init__(self) -> None:
        self.auth_dir = settings.playwright_auth_dir
        self.headless = settings.playwright_headless
        self.timeout = settings.playwright_timeout_ms
        self._browser: Optional[Browser] = None
        self._playwright: Any = None

    @property
    def auth_state_path(self) -> Path:
        """Get path to auth state file."""
        return self.auth_dir / self.AUTH_STATE_FILE

    async def __aenter__(self) -> "PlaywrightAutomation":
        self._playwright = await async_playwright().start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _get_browser(self) -> Browser:
        """Get or create browser instance."""
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
        return self._browser

    def get_auth_status(self) -> AuthStatus:
        """Check current authentication status."""
        if not self.auth_state_path.exists():
            return AuthStatus(authenticated=False)

        try:
            stat = self.auth_state_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            expires_at = last_modified + timedelta(days=self.AUTH_VALIDITY_DAYS)

            if datetime.now() > expires_at:
                return AuthStatus(
                    authenticated=False,
                    last_authenticated=last_modified,
                    expires_at=expires_at,
                    error="Authentication has expired",
                )

            return AuthStatus(
                authenticated=True,
                last_authenticated=last_modified,
                expires_at=expires_at,
            )
        except Exception as e:
            return AuthStatus(authenticated=False, error=str(e))

    async def _create_authenticated_context(self) -> BrowserContext:
        """Create a browser context with saved authentication state."""
        status = self.get_auth_status()
        if not status.authenticated:
            if status.error:
                raise AuthenticationExpired()
            raise AuthenticationRequired()

        browser = await self._get_browser()

        # Load saved state
        with open(self.auth_state_path, "r") as f:
            storage_state = json.load(f)

        context = await browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        context.set_default_timeout(self.timeout)

        return context

    async def start_auth_session(
        self,
        on_ready: Optional[Callable[[], None]] = None,
    ) -> bool:
        """
        Start an authentication session for the user to log in manually.

        Opens a browser window to Google accounts for manual login.
        Returns True when user completes authentication and state is saved.
        """
        settings.ensure_directories()
        browser = await self._get_browser()

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        context.set_default_timeout(self.timeout)

        page = await context.new_page()

        try:
            # Navigate to Google Maps which will trigger login if needed
            await page.goto("https://www.google.com/maps")

            if on_ready:
                on_ready()

            # Wait for user to complete login
            # We detect successful login by checking for the account button/menu
            print("\n" + "=" * 60)
            print("AUTHENTICATION REQUIRED")
            print("=" * 60)
            print("A browser window has opened.")
            print("Please log in to your Google account.")
            print("After logging in, this will automatically detect completion.")
            print("=" * 60 + "\n")

            # Wait for signs of being logged in
            # Google Maps shows a profile button when logged in
            try:
                # Wait for either the account button or the "Sign in" prompt to disappear
                await page.wait_for_selector(
                    'button[aria-label*="Account"], img[aria-label*="Account"]',
                    timeout=300000,  # 5 minute timeout for login
                )
                print("Login detected! Saving authentication state...")

            except Exception:
                # Try alternative detection
                await asyncio.sleep(2)
                # Check if we're on maps and there's no sign-in button
                signin_button = await page.query_selector(
                    'a[href*="accounts.google.com/ServiceLogin"]'
                )
                if signin_button:
                    raise PlaywrightError(
                        message="Login not completed",
                        details="Please complete the Google sign-in process",
                    )

            # Small delay to ensure cookies are set
            await asyncio.sleep(2)

            # Save authentication state
            storage_state = await context.storage_state()
            with open(self.auth_state_path, "w") as f:
                json.dump(storage_state, f, indent=2)

            print("Authentication state saved successfully!")
            return True

        finally:
            await context.close()

    async def remove_place(
        self,
        google_maps_url: str,
        place_name: str,
    ) -> PlaceRemovalResult:
        """
        Remove a single place from saved lists.

        Args:
            google_maps_url: The Google Maps URL for the place
            place_name: Name of the place (for reporting)

        Returns:
            PlaceRemovalResult with success status
        """
        context = await self._create_authenticated_context()
        page = await context.new_page()

        try:
            # Navigate to the place
            await page.goto(google_maps_url)

            # Wait for page to load
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)  # Extra time for dynamic content

            # Look for the "Saved" button - it indicates the place is saved
            # The button text/aria-label varies, so we try multiple selectors
            saved_button = None
            selectors = [
                'button[data-value="Save"]',
                'button[aria-label*="Saved"]',
                'button[aria-label*="saved"]',
                'button:has-text("Saved")',
                '[data-tooltip*="Saved"]',
                'button[jsaction*="save"]',
            ]

            for selector in selectors:
                try:
                    saved_button = await page.wait_for_selector(selector, timeout=5000)
                    if saved_button:
                        break
                except Exception:
                    continue

            if not saved_button:
                # Place might not be saved or UI has changed
                return PlaceRemovalResult(
                    google_maps_url=google_maps_url,
                    name=place_name,
                    success=False,
                    error="Could not find save button - place may not be saved",
                )

            # Click the saved button to open the save menu
            await saved_button.click()
            await asyncio.sleep(0.5)

            # Look for the option to unsave/remove
            # This typically shows a list of saved lists with checkboxes
            unsave_selectors = [
                'div[role="checkbox"][aria-checked="true"]',
                'button:has-text("Remove")',
                'li:has-text("Remove")',
                '[aria-label*="Remove"]',
            ]

            for selector in unsave_selectors:
                try:
                    unsave_element = await page.wait_for_selector(selector, timeout=3000)
                    if unsave_element:
                        await unsave_element.click()
                        await asyncio.sleep(0.5)
                        break
                except Exception:
                    continue

            # Wait for the action to complete
            await asyncio.sleep(settings.removal_action_delay_ms / 1000.0)

            return PlaceRemovalResult(
                google_maps_url=google_maps_url,
                name=place_name,
                success=True,
            )

        except Exception as e:
            return PlaceRemovalResult(
                google_maps_url=google_maps_url,
                name=place_name,
                success=False,
                error=str(e),
            )

        finally:
            await page.close()
            await context.close()

    async def remove_places_batch(
        self,
        places: list[dict[str, str]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[PlaceRemovalResult]:
        """
        Remove multiple places from saved lists.

        Args:
            places: List of dicts with 'url' and 'name' keys
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of removal results
        """
        results: list[PlaceRemovalResult] = []
        total = len(places)

        for i, place in enumerate(places):
            if progress_callback:
                progress_callback(i, total, f"Removing: {place['name']}")

            result = await self.remove_place(
                google_maps_url=place["url"],
                place_name=place["name"],
            )
            results.append(result)

            # Delay between removals to avoid detection
            if i < total - 1:
                await asyncio.sleep(settings.removal_action_delay_ms / 1000.0)

        if progress_callback:
            progress_callback(total, total, "Removal complete")

        return results


# Convenience functions
async def get_auth_status() -> AuthStatus:
    """Get current authentication status."""
    automation = PlaywrightAutomation()
    return automation.get_auth_status()


async def start_authentication() -> bool:
    """Start authentication flow."""
    async with PlaywrightAutomation() as automation:
        return await automation.start_auth_session()


async def remove_places(
    places: list[dict[str, str]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[PlaceRemovalResult]:
    """Remove places from saved lists."""
    async with PlaywrightAutomation() as automation:
        return await automation.remove_places_batch(places, progress_callback)
