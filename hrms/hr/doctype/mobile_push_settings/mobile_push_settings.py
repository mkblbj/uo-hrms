# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class MobilePushSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		announcement: DF.Check
		approval: DF.Check
		shift_change: DF.Check
		shift_reminder: DF.Check
		user: DF.Link
	# end: auto-generated types

	pass
