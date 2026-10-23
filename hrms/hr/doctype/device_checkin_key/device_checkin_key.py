# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class DeviceCheckinKey(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		device_name: DF.Data | None
		employee: DF.Link
		key_id: DF.Data
		last_used: DF.Datetime | None
		public_key: DF.SmallText
		user: DF.Link
	# end: auto-generated types

	pass
