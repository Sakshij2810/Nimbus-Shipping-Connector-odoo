from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from .nimbus_api import NimbusAPI

_logger = logging.getLogger(__name__)

class DeliveryNimbus(models.Model):
    """Extends delivery.carrier to add Nimbus Shipping integration"""
    
    _inherit = 'delivery.carrier'

    # Add Nimbus to the delivery type selection
    delivery_type = fields.Selection(
        selection_add=[('nimbus', 'Nimbus Shipping')],
        ondelete={'nimbus': 'set default'}
    )
    
    # Configuration fields
    nimbus_api_key = fields.Char(
        string='API Key',
        help="Your Nimbus API key - get this from your Nimbus account",
        groups="base.group_system"
    )
    
    nimbus_account_id = fields.Char(
        string='Account ID',
        help="Your Nimbus account identifier",
        groups="base.group_system"
    )
    
    nimbus_sandbox = fields.Boolean(
        string='Use Sandbox',
        help="Enable to use Nimbus sandbox environment for testing"
    )
    
    nimbus_default_package_type = fields.Many2one(
        'stock.package.type',
        string='Default Package Type',
        help="Default package type to use when calculating shipping rates"
    )
    
    nimbus_service_code = fields.Char(
        string='Default Service Code',
        help="Default service code if not specified per product"
    )

    def nimbus_rate_shipment(self, order):
        """
        Calculate shipping rates for an order
        :param order: sale.order record
        :return: dict with rate information
        """
        self.ensure_one()
        
        if not self.nimbus_api_key or not self.nimbus_account_id:
            raise UserError(_("Nimbus API credentials are not configured"))
        
        # Initialize API client
        nimbus_api = NimbusAPI(
            self.nimbus_api_key,
            self.nimbus_account_id,
            self.nimbus_sandbox
        )
        
        # Prepare package information
        package_info = self._prepare_nimbus_package_info(order)
        
        try:
            # Get rates from Nimbus API
            response = nimbus_api.get_rates(package_info)
            
            # Find the rate for our default service code
            rate = next(
                (r for r in response.get('rates', []) 
                 if r.get('service_code') == self.nimbus_service_code),
                None
            )
            
            if not rate:
                return {
                    'success': False,
                    'price': 0.0,
                    'error_message': _("No matching service rate found"),
                    'warning_message': None
                }
            
            return {
                'success': True,
                'price': rate['amount'],
                'error_message': None,
                'warning_message': None,
                'transit_days': rate.get('transit_days', 0)
            }
            
        except Exception as e:
            _logger.exception("Nimbus rate calculation failed")
            return {
                'success': False,
                'price': 0.0,
                'error_message': str(e),
                'warning_message': None
            }

    def nimbus_send_shipping(self, pickings):
        """
        Create shipment in Nimbus and get tracking info
        :param pickings: stock.picking recordset
        :return: list of dicts with shipping info
        """
        self.ensure_one()
        
        if not self.nimbus_api_key or not self.nimbus_account_id:
            raise UserError(_("Nimbus API credentials are not configured"))
        
        nimbus_api = NimbusAPI(
            self.nimbus_api_key,
            self.nimbus_account_id,
            self.nimbus_sandbox
        )
        
        result = []
        for picking in pickings:
            # Prepare shipment data
            shipment_data = self._prepare_nimbus_shipment_data(picking)
            
            try:
                # Create shipment in Nimbus
                response = nimbus_api.create_shipment(shipment_data)
                
                # Store tracking reference
                picking.carrier_tracking_ref = response['tracking_number']
                
                # Generate label (implementation depends on Nimbus API)
                if response.get('label_url'):
                    self.env['ir.attachment'].create({
                        'name': f"Nimbus Label {response['tracking_number']}",
                        'type': 'url',
                        'url': response['label_url'],
                        'res_model': picking._name,
                        'res_id': picking.id,
                    })
                
                result.append({
                    'exact_price': response['shipping_cost'],
                    'tracking_number': response['tracking_number']
                })
                
            except Exception as e:
                raise UserError(_("Nimbus shipment creation failed: %s") % str(e))
        
        return result

    def nimbus_get_tracking_link(self, picking):
        """
        Generate tracking URL for a shipment
        :param picking: stock.picking record
        :return: tracking URL as string
        """
        self.ensure_one()
        
        if not picking.carrier_tracking_ref:
            return ""
            
        # NOTE: Replace with actual Nimbus tracking URL format
        return f"https://track.nimbus.com/{picking.carrier_tracking_ref}"

    def _prepare_nimbus_package_info(self, order):
        """
        Prepare package information for rate request
        :param order: sale.order record
        :return: dict with package details
        """
        weight = sum(
            line.product_id.weight * line.product_uom_qty 
            for line in order.order_line
            if line.product_id.weight and not line.is_delivery
        ) or 1.0  # Default to 1kg if no weight
        
        return {
            'weight': weight,
            'length': self.nimbus_default_package_type.packaging_length or 30,
            'width': self.nimbus_default_package_type.width or 20,
            'height': self.nimbus_default_package_type.height or 10,
            'value': order.amount_total,
            'origin': {
                'zip': order.warehouse_id.partner_id.zip or '',
                'country': order.warehouse_id.partner_id.country_id.code or '',
            },
            'destination': {
                'zip': order.partner_shipping_id.zip or '',
                'country': order.partner_shipping_id.country_id.code or '',
            },
            'service_code': self.nimbus_service_code,
        }

    def _prepare_nimbus_shipment_data(self, picking):
        """
        Prepare shipment data for creation request
        :param picking: stock.picking record
        :return: dict with shipment details
        """
        order = picking.sale_id
        return {
            'service_code': self.nimbus_service_code,
            'ship_from': {
                'name': order.warehouse_id.partner_id.name,
                'address1': order.warehouse_id.partner_id.street,
                'city': order.warehouse_id.partner_id.city,
                'state': order.warehouse_id.partner_id.state_id.code,
                'zip': order.warehouse_id.partner_id.zip,
                'country': order.warehouse_id.partner_id.country_id.code,
                'phone': order.warehouse_id.partner_id.phone,
            },
            'ship_to': {
                'name': order.partner_shipping_id.name,
                'address1': order.partner_shipping_id.street,
                'city': order.partner_shipping_id.city,
                'state': order.partner_shipping_id.state_id.code,
                'zip': order.partner_shipping_id.zip,
                'country': order.partner_shipping_id.country_id.code,
                'phone': order.partner_shipping_id.phone,
            },
            'packages': [{
                'weight': sum(
                    move.product_id.weight * move.product_uom_qty 
                    for move in picking.move_lines
                    if move.product_id.weight
                ) or 1.0,
                'length': self.nimbus_default_package_type.packaging_length or 30,
                'width': self.nimbus_default_package_type.width or 20,
                'height': self.nimbus_default_package_type.height or 10,
            }],
            'reference': picking.name,
            'order_id': order.name,
        }