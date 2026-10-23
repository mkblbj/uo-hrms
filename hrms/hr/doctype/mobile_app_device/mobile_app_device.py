# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class MobileAppDevice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_version: DF.Data | None
		bundle_id: DF.Data
		device_model: DF.Data | None
		device_token: DF.Data
		environment: DF.Literal["sandbox", "production"]
		installation_id: DF.Data | None
		last_seen: DF.Datetime | None
		os_version: DF.Data | None
		user: DF.Link
	# end: auto-generated types

	pass
