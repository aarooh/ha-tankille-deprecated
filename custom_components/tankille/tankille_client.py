"""Tankille API client."""

import asyncio
import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
import async_timeout
import aiofiles

_LOGGER = logging.getLogger(__name__)

# API Constants
API_URL = "https://api.tankille.fi"


class TankilleError(Exception):
    """Base exception for Tankille API errors."""

    pass


class AuthenticationError(TankilleError):
    """Authentication related errors."""

    pass


class ApiError(TankilleError):
    """API request errors."""

    pass


class TankilleClient:
    """Client to interact with the Tankille API."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the Tankille client."""
        self.token = ""
        self.refresh_token = ""

        self.token_cache = {"last_fetch": 0, "data": {}}

        self.options = {
            "device": "Android SDK built for x86_64 (03280ceb8a5367a6)",
            "userAgent": "FuelFellow/3.6.2 (Android SDK built for x86_64; Android 9)",
        }

        self.headers = {
            "User-Agent": "FuelFellow/3.6.2 (Android SDK built for x86_64; Android 9)",
            "Host": "api.tankille.fi",
            "Content-Type": "application/json",
        }

        self.session = session
        self._token_file = ".tankille_tokens.json"
        # Don't load tokens in __init__ since it's synchronous
        # We'll load them when needed in async methods
        self._tokens_loaded = False

    async def _load_tokens_from_file(self):
        """Load tokens from local file if available."""
        if self._tokens_loaded:
            return
            
        if os.path.exists(self._token_file):
            try:
                async with aiofiles.open(self._token_file, "r") as f:
                    content = await f.read()
                    data = json.loads(content)
                    self.token = data.get("access_token", "")
                    self.refresh_token = data.get("refresh_token", "")
                    self.token_cache = data.get("token_cache", self.token_cache)
            except Exception as e:
                _LOGGER.error("Error loading tokens from file: %s", e)
        
        self._tokens_loaded = True

    async def _save_tokens_to_file(self):
        """Save tokens to local file."""
        try:
            data = {
                "access_token": self.token,
                "refresh_token": self.refresh_token,
                "token_cache": self.token_cache,
            }
            
            async with aiofiles.open(self._token_file, "w") as f:
                await f.write(json.dumps(data))
        except Exception as e:
            _LOGGER.error("Error saving tokens to file: %s", e)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a client session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _auth_async(self):
        """Authenticate user if refresh token exists."""
        await self._load_tokens_from_file()
        
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available. Please login first.")

        self.token = await self._get_session_token_async(
            {"refreshToken": self.refresh_token}
        )

    async def _get_refresh_token_async(
        self, login_options: Dict[str, Any]
    ) -> Dict[str, str]:
        """Get refresh token by logging in with email and password."""
        session = await self._get_session()

        try:
            async with async_timeout.timeout(10):
                response = await session.post(
                    f"{API_URL}/auth/login",
                    json={"device": self.options["device"], **login_options},
                    headers=self.headers,
                )

                if response.status != 200:
                    error_text = await response.text()
                    raise AuthenticationError(
                        f"Error authenticating: {response.status} - {error_text}"
                    )

                return await response.json()

        except asyncio.TimeoutError:
            raise ApiError("Timeout while connecting to Tankille API")
        except aiohttp.ClientError as err:
            raise ApiError(f"Error connecting to Tankille API: {err}")

    async def _get_session_token_async(self, refresh_token_data: Dict[str, str]) -> str:
        """Get session token using refresh token."""
        time_since_last_fetch = (
            datetime.datetime.now().timestamp() - self.token_cache["last_fetch"]
        )

        # 10h cache for access token (expires in 12 hours)
        if time_since_last_fetch <= 36000 and "accessToken" in self.token_cache.get(
            "data", {}
        ):
            return self.token_cache["data"]["accessToken"]

        session = await self._get_session()

        try:
            async with async_timeout.timeout(10):
                response = await session.post(
                    f"{API_URL}/auth/refresh",
                    json={"token": refresh_token_data["refreshToken"]},
                    headers=self.headers,
                )

                if response.status != 200:
                    error_text = await response.text()
                    raise AuthenticationError(
                        f"Error refreshing token: {response.status} - {error_text}"
                    )

                data = await response.json()

                if data and "accessToken" in data:
                    self.token_cache = {
                        "last_fetch": datetime.datetime.now().timestamp(),
                        "data": data,
                    }

                    return data["accessToken"]

                raise AuthenticationError("No access token found in response")

        except asyncio.TimeoutError:
            raise ApiError("Timeout while connecting to Tankille API")
        except aiohttp.ClientError as err:
            raise ApiError(f"Error connecting to Tankille API: {err}")

    async def login(self, email: str, password: str, force: bool = False) -> str:
        """
        Login with email and password (asynchronous).

        Args:
            email: User email
            password: User password  
            force: Force login even if already logged in

        Returns:
            Access token

        Raises:
            AuthenticationError: If login fails
        """
        # Load tokens before checking if logged in
        await self._load_tokens_from_file()
        
        login_options = {"email": email, "password": password, "force": force}

        if not email or not password:
            raise AuthenticationError("Email or password missing")

        # Check if already logged in
        if not force and self.token:
            # Try to use the existing token
            try:
                await self._auth_async()
                return self.token
            except AuthenticationError:
                # If token is invalid, proceed with login
                pass

        token_data = await self._get_refresh_token_async(login_options)
        access_token = await self._get_session_token_async(token_data)

        self.token = access_token
        self.refresh_token = token_data["refreshToken"]
        await self._save_tokens_to_file()

        return access_token

    async def get_stations(self) -> List[Dict]:
        """
        Get list of all stations (asynchronous).

        Returns:
            List of stations

        Raises:
            ApiError: If API request fails
            AuthenticationError: If not authenticated
        """
        await self._auth_async()

        session = await self._get_session()

        try:
            async with async_timeout.timeout(10):
                response = await session.get(
                    f"{API_URL}/stations",
                    headers={**self.headers, "x-access-token": self.token},
                )

                if response.status != 200:
                    error_text = await response.text()
                    raise ApiError(
                        f"Error fetching stations: {response.status} - {error_text}"
                    )

                data = await response.json()

                if not data:
                    raise ApiError("No stations found")

                return data

        except asyncio.TimeoutError:
            raise ApiError("Timeout while connecting to Tankille API")
        except aiohttp.ClientError as err:
            raise ApiError(f"Error connecting to Tankille API: {err}")

    async def get_stations_by_location(
        self, lat: float, lon: float, distance: int = 15000
    ) -> List[Dict]:
        """
        Get stations by location within distance (asynchronous).

        Args:
            lat: Latitude
            lon: Longitude
            distance: Search radius in meters (default: 15000)

        Returns:
            List of stations

        Raises:
            ApiError: If API request fails
            AuthenticationError: If not authenticated
        """
        if lat is None or lon is None:
            raise ApiError("Location coordinates (lat, lon) are required")

        if not isinstance(distance, (int, float)):
            raise ApiError("Distance must be a number")

        await self._auth_async()

        session = await self._get_session()

        try:
            async with async_timeout.timeout(10):
                response = await session.get(
                    f"{API_URL}/stations?location={lon},{lat}&distance={distance}",
                    headers={**self.headers, "x-access-token": self.token},
                )

                if response.status != 200:
                    error_text = await response.text()
                    raise ApiError(
                        f"Error fetching stations by location: {response.status} - {error_text}"
                    )

                data = await response.json()

                if not data:
                    raise ApiError("No stations found")

                return data

        except asyncio.TimeoutError:
            raise ApiError("Timeout while connecting to Tankille API")
        except aiohttp.ClientError as err:
            raise ApiError(f"Error connecting to Tankille API: {err}")

    async def get_station(self, station_id: str, days: int = 14) -> Dict:
        """
        Get specific station by ID with price history (asynchronous).

        Args:
            station_id: Station ID
            days: Number of days of price history (default: 14)

        Returns:
            Station details with price history

        Raises:
            ApiError: If API request fails
            AuthenticationError: If not authenticated
        """
        if not station_id:
            raise ApiError("Station ID is required")

        await self._auth_async()

        # Calculate date for price history
        since = datetime.datetime.now() - datetime.timedelta(days=days)
        since_str = since.isoformat()

        session = await self._get_session()

        try:
            async with async_timeout.timeout(10):
                response = await session.get(
                    f"{API_URL}/stations/{station_id}/prices?since={since_str}",
                    headers={**self.headers, "x-access-token": self.token},
                )

                if response.status != 200:
                    error_text = await response.text()
                    raise ApiError(
                        f"Error fetching station: {response.status} - {error_text}"
                    )

                data = await response.json()

                if not data:
                    raise ApiError("Station not found")

                return data

        except asyncio.TimeoutError:
            raise ApiError("Timeout while connecting to Tankille API")
        except aiohttp.ClientError as err:
            raise ApiError(f"Error connecting to Tankille API: {err}")

    # --- Utility methods ---

    def print_station_info(self, station: Dict) -> None:
        """
        Print formatted station information.

        Args:
            station: Station data
        """
        print(f"Station: {station['name']} ({station['chain']})")
        print(f"Address: {station['address']['street']}, {station['address']['city']}")
        print(f"Available fuels: {', '.join(station['fuels'])}")
        print("Latest prices:")

        # Sort by fuel type
        sorted_prices = sorted(station["price"], key=lambda x: x["tag"])

        for price in sorted_prices:
            updated = datetime.datetime.fromisoformat(
                price["updated"].replace("Z", "+00:00")
            )
            print(
                f"  {price['tag']}: {price['price']}€ (updated: {updated.strftime('%Y-%m-%d %H:%M')})"
            )