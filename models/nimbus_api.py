import requests
import logging
from odoo import exceptions, _

_logger = logging.getLogger(__name__)

class NimbusAPI:
    """Handles all communication with Nimbus Shipping API"""
    
    def __init__(self, api_key, account_id, sandbox=False):
        """
        Initialize API client
        :param api_key: Your Nimbus API key
        :param account_id: Your Nimbus account ID
        :param sandbox: Boolean to use sandbox environment
        """
        # NOTE: Replace these base URLs with actual Nimbus API endpoints
        self.base_url = "https://api.sandbox.nimbus.com/v1/" if sandbox else "https://api.nimbus.com/v1/"
        self.api_key = api_key
        self.account_id = account_id
        self.timeout = 10  # seconds

    def _make_request(self, endpoint, method='GET', payload=None):
        """Generic request handler"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Account-ID': self.account_id,
            'Content-Type': 'application/json'
        }

        try:
            _logger.info(f"Nimbus API Request: {method} {url}")
            
            if method == 'GET':
                response = requests.get(url, headers=headers, params=payload, timeout=self.timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            else:
                raise exceptions.UserError(_("Unsupported HTTP method"))

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.error(f"Nimbus API Error: {str(e)}")
            raise exceptions.UserError(_("Nimbus API Error: %s") % str(e))

    def get_rates(self, package_info):
        """
        Get shipping rates for a package
        :param package_info: Dict containing package details
        :return: List of available shipping rates
        """
        # Example package_info structure:
        # {
        #   'weight': 1.5,  # in kg
        #   'length': 30,   # in cm
        #   'width': 20,
        #   'height': 10,
        #   'value': 100.0, # monetary value
        #   'origin': {'zip': '10001', 'country': 'US'},
        #   'destination': {'zip': '90210', 'country': 'US'}
        # }
        return self._make_request('rates', 'POST', package_info)

    def create_shipment(self, shipment_data):
        """Create a new shipment and get label"""
        return self._make_request('shipments', 'POST', shipment_data)

    def cancel_shipment(self, tracking_number):
        """Cancel an existing shipment"""
        return self._make_request(f'shipments/{tracking_number}/cancel', 'POST')

    def get_tracking(self, tracking_number):
        """Get tracking information for a shipment"""
        return self._make_request(f'tracking/{tracking_number}', 'GET')