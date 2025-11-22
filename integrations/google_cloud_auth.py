"""
Enhanced Google Cloud Authentication and Credential Management

Provides secure, robust authentication for Google Cloud services including:
- Vertex AI
- Cloud Storage (GCS)
- Gmail API
- Automatic credential validation and refresh
- Environment-based configuration

Date: 2025-01-11
Task: #13 - Enhance Google Cloud Integration
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import storage
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logger.error("Google Cloud libraries not available. Install with: pip install google-auth google-cloud-storage google-api-python-client")
    raise ImportError("Google Cloud authentication requires additional packages")


@dataclass
class GoogleCloudConfig:
    """Configuration for Google Cloud services."""
    project_id: str
    credentials_path: Optional[str] = None
    service_account_email: Optional[str] = None
    scopes: List[str] = field(default_factory=lambda: [
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ])
    region: str = 'us-central1'
    vertex_ai_location: str = 'us-central1'


class GoogleCloudAuthManager:
    """
    Enhanced authentication manager for Google Cloud services.

    Features:
    - Automatic credential discovery and validation
    - Service account and ADC (Application Default Credentials) support
    - Credential refresh and token management
    - Service-specific authentication
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[GoogleCloudConfig] = None):
        """
        Initialize the Google Cloud authentication manager.

        Args:
            config: Optional configuration, auto-detected if not provided
        """
        self.config = config or self._auto_detect_config()
        self._credentials_cache: Dict[str, Any] = {}
        self._service_cache: Dict[str, Any] = {}
        self._last_refresh: Dict[str, float] = {}
        self._refresh_interval = 1800  # 30 minutes

        logger.info(f"GoogleCloudAuthManager initialized for project: {self.config.project_id}")

    def _auto_detect_config(self) -> GoogleCloudConfig:
        """Auto-detect Google Cloud configuration from environment."""
        config = GoogleCloudConfig(
            project_id=os.getenv('GOOGLE_PROJECT_ID') or
                     os.getenv('GOOGLE_CLOUD_PROJECT') or
                     'default-project',
            credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )

        # Try to get credentials path
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and Path(creds_path).exists():
            config.credentials_path = creds_path

            # Try to extract service account email from credentials file
            try:
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                    config.service_account_email = creds_data.get('client_email')
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"Could not parse service account email from {creds_path}")

        return config

    async def get_credentials(self, service_name: str = 'default') -> Any:
        """
        Get authenticated credentials for Google Cloud services.

        Args:
            service_name: Name of the service (for caching)

        Returns:
            Google auth credentials object

        Raises:
            GoogleCloudAuthError: If authentication fails
        """
        # Check cache first
        if self._should_refresh_credentials(service_name):
            try:
                credentials = await self._create_credentials()
                self._credentials_cache[service_name] = credentials
                self._last_refresh[service_name] = time.time()

                logger.debug(f"Credentials refreshed for service: {service_name}")
            except Exception as e:
                logger.error(f"Failed to refresh credentials for {service_name}: {e}")
                raise GoogleCloudAuthError(f"Authentication failed: {e}")

        return self._credentials_cache[service_name]

    async def _create_credentials(self) -> Any:
        """Create Google Cloud credentials."""
        try:
            # Try service account credentials first
            if self.config.credentials_path:
                logger.debug(f"Using service account credentials: {self.config.credentials_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.credentials_path,
                    scopes=self.config.scopes
                )

            else:
                # Try Application Default Credentials
                logger.debug("Attempting Application Default Credentials")
                credentials, project = google_auth_default(scopes=self.config.scopes)

                # Update project if detected
                if project and project != self.config.project_id:
                    logger.info(f"Detected project ID from ADC: {project}")
                    self.config.project_id = project

            # Refresh if needed
            if not credentials.valid:
                logger.debug("Refreshing credentials")
                request = Request()
                credentials.refresh(request)

            return credentials

        except DefaultCredentialsError as e:
            raise GoogleCloudAuthError(f"No valid credentials found: {e}")
        except Exception as e:
            raise GoogleCloudAuthError(f"Credential creation failed: {e}")

    def _should_refresh_credentials(self, service_name: str) -> bool:
        """Check if credentials should be refreshed."""
        if service_name not in self._credentials_cache:
            return True

        last_refresh = self._last_refresh.get(service_name, 0)
        return (time.time() - last_refresh) > self._refresh_interval

    async def get_gcs_client(self) -> storage.Client:
        """
        Get authenticated Google Cloud Storage client.

        Returns:
            GCS client ready for operations
        """
        credentials = await self.get_credentials('gcs')
        client = storage.Client(
            project=self.config.project_id,
            credentials=credentials
        )

        logger.debug("GCS client created successfully")
        return client

    async def get_gmail_service(self):
        """
        Get authenticated Gmail API service.

        Returns:
            Gmail API service object
        """
        if 'gmail' not in self._service_cache or self._should_refresh_service('gmail'):
            credentials = await self.get_credentials('gmail')

            try:
                service = build('gmail', 'v1', credentials=credentials)
                self._service_cache['gmail'] = service
                self._last_refresh['gmail'] = time.time()

                logger.debug("Gmail service created successfully")
            except HttpError as e:
                raise GoogleCloudAuthError(f"Gmail service creation failed: {e}")

        return self._service_cache['gmail']

    async def get_vertex_ai_service(self):
        """
        Get Vertex AI service client.

        Returns:
            Vertex AI client (placeholder for future implementation)
        """
        # For now, return credentials that can be used with Vertex AI SDK
        credentials = await self.get_credentials('vertex_ai')

        # In a full implementation, this would create a Vertex AI client
        # For now, we return the credentials for use with the SDK
        logger.debug("Vertex AI credentials prepared")
        return credentials

    def _should_refresh_service(self, service_name: str) -> bool:
        """Check if a service should be refreshed."""
        if service_name not in self._service_cache:
            return True

        last_refresh = self._last_refresh.get(service_name, 0)
        return (time.time() - last_refresh) > self._refresh_interval

    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate all Google Cloud credentials and services.

        Returns:
            Dictionary with validation results for each service
        """
        results = {
            'overall_status': 'unknown',
            'services': {},
            'errors': []
        }

        services_to_test = [
            ('credentials', self._test_basic_credentials),
            ('gcs', self._test_gcs_access),
            ('gmail', self._test_gmail_access),
            ('vertex_ai', self._test_vertex_ai_access)
        ]

        all_passed = True

        for service_name, test_func in services_to_test:
            try:
                status = await test_func()
                results['services'][service_name] = status
                if not status.get('valid', False):
                    all_passed = False
            except Exception as e:
                results['services'][service_name] = {'valid': False, 'error': str(e)}
                results['errors'].append(f"{service_name}: {e}")
                all_passed = False

        results['overall_status'] = 'valid' if all_passed else 'invalid'
        return results

    async def _test_basic_credentials(self) -> Dict[str, Any]:
        """Test basic credential validity."""
        try:
            credentials = await self.get_credentials('test')
            return {
                'valid': credentials.valid,
                'project_id': self.config.project_id,
                'service_account': self.config.service_account_email
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    async def _test_gcs_access(self) -> Dict[str, Any]:
        """Test GCS access."""
        try:
            client = await self.get_gcs_client()
            # Try to list buckets (will fail if no permission, but tests auth)
            buckets = list(client.list_buckets(max_results=1))
            return {
                'valid': True,
                'buckets_accessible': len(buckets) > 0
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    async def _test_gmail_access(self) -> Dict[str, Any]:
        """Test Gmail API access."""
        try:
            service = await self.get_gmail_service()
            # Test basic API call
            profile = service.users().getProfile(userId='me').execute()
            return {
                'valid': True,
                'email_address': profile.get('emailAddress')
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    async def _test_vertex_ai_access(self) -> Dict[str, Any]:
        """Test Vertex AI access."""
        try:
            # For now, just test that we can get credentials
            credentials = await self.get_credentials('vertex_ai')
            return {
                'valid': credentials.valid,
                'region': self.config.vertex_ai_location
            }
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information."""
        return {
            'project_id': self.config.project_id,
            'credentials_path': self.config.credentials_path,
            'service_account_email': self.config.service_account_email,
            'region': self.config.region,
            'vertex_ai_location': self.config.vertex_ai_location,
            'scopes': self.config.scopes
        }

    def _check_version_compatibility(
        self,
        agent_version: str,
        requirement: Optional[str]
    ) -> bool:
        """
        Check if agent version meets requirement.

        Supports:
        - ">=1.0" - greater than or equal
        - "<=2.0" - less than or equal
        - "==1.5" - exact match
        - "1.0" - exact match (no operator)

        Args:
            agent_version: Agent's capability version
            requirement: Version requirement string

        Returns:
            True if compatible, False otherwise
        """
        if not requirement:
            return True

        requirement = requirement.strip()

        # Parse operator and version
        if requirement.startswith(">="):
            op = ">="
            req_ver = requirement[2:].strip()
        elif requirement.startswith("<="):
            op = "<="
            req_ver = requirement[2:].strip()
        elif requirement.startswith("=="):
            op = "=="
            req_ver = requirement[2:].strip()
        elif requirement.startswith(">"):
            op = ">"
            req_ver = requirement[1:].strip()
        elif requirement.startswith("<"):
            op = "<"
            req_ver = requirement[1:].strip()
        else:
            op = "=="
            req_ver = requirement

        # Convert versions to tuples for comparison
        try:
            agent_ver_tuple = tuple(map(int, agent_version.split('.')))
            req_ver_tuple = tuple(map(int, req_ver.split('.')))
        except (ValueError, AttributeError):
            # If version parsing fails, assume compatible
            return True

        # Perform comparison
        if op == ">=":
            return agent_ver_tuple >= req_ver_tuple
        elif op == "<=":
            return agent_ver_tuple <= req_ver_tuple
        elif op == ">":
            return agent_ver_tuple > req_ver_tuple
        elif op == "<":
            return agent_ver_tuple < req_ver_tuple
        else:  # ==
            return agent_ver_tuple == req_ver_tuple


class GoogleCloudAuthError(Exception):
    """Custom exception for Google Cloud authentication errors."""
    pass


# Global instance for easy access
_google_auth_manager: Optional[GoogleCloudAuthManager] = None


def get_auth_manager() -> GoogleCloudAuthManager:
    """Get the global Google Cloud authentication manager."""
    global _google_auth_manager
    if _google_auth_manager is None:
        _google_auth_manager = GoogleCloudAuthManager()
    return _google_auth_manager


async def initialize_google_cloud() -> GoogleCloudAuthManager:
    """Initialize Google Cloud authentication globally."""
    global _google_auth_manager
    _google_auth_manager = GoogleCloudAuthManager()

    # Validate credentials on initialization
    validation = await _google_auth_manager.validate_credentials()
    if validation['overall_status'] != 'valid':
        logger.warning("Google Cloud validation failed:")
        for service, result in validation['services'].items():
            if not result.get('valid', False):
                logger.warning(f"  {service}: {result.get('error', 'Unknown error')}")

    return _google_auth_manager


# Convenience functions
async def get_gcs_client() -> storage.Client:
    """Get GCS client through the auth manager."""
    manager = get_auth_manager()
    return await manager.get_gcs_client()


async def get_gmail_service():
    """Get Gmail service through the auth manager."""
    manager = get_auth_manager()
    return await manager.get_gmail_service()


async def get_vertex_credentials():
    """Get Vertex AI credentials through the auth manager."""
    manager = get_auth_manager()
    return await manager.get_vertex_ai_service()


async def validate_google_cloud_setup() -> Dict[str, Any]:
    """Validate complete Google Cloud setup."""
    manager = get_auth_manager()
    return await manager.validate_credentials()


if __name__ == "__main__":
    # Example usage and testing
    import asyncio

    async def main():
        try:
            # Initialize
            auth_manager = await initialize_google_cloud()

            # Test validation
            validation = await validate_google_cloud_setup()
            print("Validation results:")
            print(json.dumps(validation, indent=2))

            # Show config
            config = auth_manager.get_config_info()
            print("\nConfiguration:")
            print(json.dumps(config, indent=2))

        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
