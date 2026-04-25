# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import datetime, time, timedelta
from itertools import groupby

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	create_batch,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	time_diff,
)


def round_time_to_precision(dt: datetime, precision_minutes: int, direction: str) -> datetime:
	"""
	Round datetime to the specified precision.
	
	Args:
		dt: datetime object to round
		precision_minutes: rounding precision (15, 30, or 60 minutes)
		direction: 'up' for check-in (round up), 'down' for check-out (round down)
	
	Returns:
		Rounded datetime
	
	Examples (precision=15):
		Check-in  9:00  -> 9:00
		Check-in  9:01  -> 9:15
		Check-in  9:12  -> 9:15
		Check-in  9:16  -> 9:30
		Check-out 18:00 -> 18:00
		Check-out 17:59 -> 17:45
		Check-out 17:47 -> 17:45
	"""
	if not dt or not precision_minutes:
		return dt
	
	precision_minutes = int(precision_minutes)
	minutes = dt.minute
	remainder = minutes % precision_minutes
	
	if direction == 'up':  # Check-in: round up
		if remainder == 0:
			return dt.replace(second=0, microsecond=0)
		add_minutes = precision_minutes - remainder
		return dt.replace(second=0, microsecond=0) + timedelta(minutes=add_minutes)
	else:  # Check-out: round down
		return dt.replace(second=0, microsecond=0) - timedelta(minutes=remainder)


def calculate_lunch_overlap_hours(
	in_time: datetime,
	out_time: datetime,
	lunch_start: time,
	lunch_end: time
) -> float:
	"""
	Calculate the overlap hours between work period and lunch break.
	
	Args:
		in_time: Check-in datetime
		out_time: Check-out datetime
		lunch_start: Lunch break start time
		lunch_end: Lunch break end time
	
	Returns:
		Overlap hours (float), 0 if no overlap
	
	Examples (lunch 12:00-13:00):
		9:00-18:00  -> 1.0 (full overlap)
		9:00-12:00  -> 0.0 (no overlap)
		13:00-18:00 -> 0.0 (no overlap)
		11:30-12:30 -> 0.5 (partial overlap)
		11:30-14:00 -> 1.0 (full lunch included)
	"""
	if not in_time or not out_time or not lunch_start or not lunch_end:
		return 0
	
	# Convert lunch times to datetime on the same date as in_time
	work_date = in_time.date()
	lunch_start_dt = datetime.combine(work_date, get_time(lunch_start))
	lunch_end_dt = datetime.combine(work_date, get_time(lunch_end))
	
	# If out_time is before lunch starts or in_time is after lunch ends, no overlap
	if out_time <= lunch_start_dt or in_time >= lunch_end_dt:
		return 0
	
	# Calculate actual overlap
	overlap_start = max(in_time, lunch_start_dt)
	overlap_end = min(out_time, lunch_end_dt)
	
	if overlap_end > overlap_start:
		return (overlap_end - overlap_start).total_seconds() / 3600
	return 0

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.setup.doctype.holiday_list.holiday_list import is_half_holiday, is_holiday

from hrms.hr.doctype.attendance.attendance import mark_attendance
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift, get_shift_details
from hrms.utils import get_date_range
from hrms.utils.holiday_list import get_holiday_dates_between

EMPLOYEE_CHUNK_SIZE = 50


class ShiftType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_check_out_after_shift_end_time: DF.Int
		allow_overtime: DF.Check
		auto_update_last_sync: DF.Check
		begin_check_in_before_shift_start_time: DF.Int
		color: DF.Literal[
			"Blue", "Cyan", "Fuchsia", "Green", "Lime", "Orange", "Pink", "Red", "Violet", "Yellow"
		]
		determine_check_in_and_check_out: DF.Literal[
			"Alternating entries as IN and OUT during the same shift",
			"Strictly based on Log Type in Employee Checkin",
		]
		early_exit_grace_period: DF.Int
		enable_auto_attendance: DF.Check
		enable_early_exit_marking: DF.Check
		enable_late_entry_marking: DF.Check
		end_time: DF.Time
		holiday_list: DF.Link | None
		last_sync_of_checkin: DF.Datetime | None
		late_entry_grace_period: DF.Int
		mark_auto_attendance_on_holidays: DF.Check
		overtime_type: DF.Link | None
		process_attendance_after: DF.Date | None
		start_time: DF.Time
		working_hours_calculation_based_on: DF.Literal[
			"First Check-in and Last Check-out", "Every Valid Check-in and Check-out"
		]
		working_hours_threshold_for_absent: DF.Float
		working_hours_threshold_for_half_day: DF.Float
	# end: auto-generated types

	def validate(self):
		start = get_time(self.start_time)
		end = get_time(self.end_time)
		self.validate_same_start_and_end(start, end)
		self.validate_circular_shift(start, end)
		self.validate_unlinked_logs()

	def validate_same_start_and_end(self, start_time: datetime.time, end_time: datetime.time):
		if start_time == end_time:
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Start time and end time cannot be same."),
			)

	def validate_circular_shift(self, start_time: datetime.time, end_time: datetime.time):
		shift_start, shift_end = self.get_shift_start_and_shift_end(start_time, end_time)
		if self.get_total_shift_duration_in_minutes(shift_start, shift_end) >= 1440:
			max_label = self.get_max_shift_buffer_label()
			frappe.throw(
				title=_("Invalid Shift Times"),
				msg=_("Please reduce {0} to avoid shift time overlapping with itself").format(
					frappe.bold(max_label)
				),
			)

	def get_shift_start_and_shift_end(
		self, start_time: datetime.time, end_time: datetime.time
	) -> tuple[datetime]:
		shift_start = datetime.combine(getdate(), start_time)
		if start_time < end_time:
			shift_end = datetime.combine(getdate(), end_time)
		elif start_time > end_time:
			shift_end = datetime.combine(add_days(getdate(), 1), end_time)
		return shift_start, shift_end

	def get_total_shift_duration_in_minutes(
		self, shift_start: datetime.time, shift_end: datetime.time
	) -> int:
		return (
			(round(time_diff(shift_end, shift_start).total_seconds() / 60))
			+ (self.allow_check_out_after_shift_end_time or 0)
			+ (self.begin_check_in_before_shift_start_time or 0)
		)

	def get_max_shift_buffer_label(self) -> str:
		labels = {
			_(
				self.meta.get_label("allow_check_out_after_shift_end_time")
			): self.allow_check_out_after_shift_end_time,
			_(
				self.meta.get_label("begin_check_in_before_shift_start_time")
			): self.begin_check_in_before_shift_start_time,
		}
		return max(labels, key=labels.get)

	def validate_unlinked_logs(self):
		if self.is_field_modified("start_time") and self.unlinked_checkins_exist():
			frappe.throw(
				title=_("Unmarked Check-in Logs Found"),
				msg=_("Mark attendance for existing check-in/out logs before changing shift settings"),
			)

	def is_field_modified(self, fieldname):
		return not self.is_new() and self.has_value_changed(fieldname)

	def unlinked_checkins_exist(self):
		return frappe.db.exists(
			"Employee Checkin",
			{"shift": self.name, "attendance": ["is", "not set"], "skip_auto_attendance": 0, "offshift": 0},
		)

	@frappe.whitelist()
	def process_auto_attendance(self, is_manually_triggered: int | bool = False) -> None | str:
		if self.has_incorrect_shift_config():
			return

		logs = self.get_employee_checkins()
		if is_manually_triggered:
			if len(logs) > 1000 or frappe.flags.test_bg_job:
				job_id = "process_auto_attendance_" + self.name
				job = frappe.enqueue(self._process, logs=logs, timeout=1200, job_id=job_id, deduplicate=True)
				return f"Attendance marking has been queued. It may take a few minutes. You can monitor the job status {get_link_to_form('RQ Job',job.id,label='here')}"
			else:
				try:
					self._process(logs)
					return "Attendance has been marked as per employee check-ins."
				except Exception as e:
					error_log = frappe.log_error(e)
					return f"An error occured during marking attendance. Refer the full error log {get_link_to_form('Error Log',error_log.name,label='here')}"
		else:
			self._process(logs)

	def has_incorrect_shift_config(self):
		return (
			not cint(self.enable_auto_attendance)
			or not self.process_attendance_after
			or not self.last_sync_of_checkin
		)

	def _process(self, logs):
		group_key = lambda x: (x["employee"], x["shift_start"])  # noqa
		for key, group in groupby(sorted(logs, key=group_key), key=group_key):
			single_shift_logs = list(group)
			attendance_date = key[1].date()
			employee = key[0]

			if not self.should_mark_attendance(employee, attendance_date):
				continue

			working_hours_threshold_for_half_day = flt(self.working_hours_threshold_for_half_day)
			working_hours_threshold_for_absent = flt(self.working_hours_threshold_for_absent)

			if self.is_half_holiday(employee, attendance_date):
				working_hours_threshold_for_half_day = flt(self.working_hours_threshold_for_half_day) / 2
				working_hours_threshold_for_absent = flt(self.working_hours_threshold_for_absent) / 2

			overtime_type = single_shift_logs[0].get("overtime_type")
			(
				attendance_status,
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
			) = self.get_attendance(
				single_shift_logs, working_hours_threshold_for_absent, working_hours_threshold_for_half_day
			)

			mark_attendance_and_link_log(
				single_shift_logs,
				attendance_status,
				attendance_date,
				working_hours,
				late_entry,
				early_exit,
				in_time,
				out_time,
				self.name,
				overtime_type,
			)

		# commit after processing checkin logs to avoid losing progress
		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep

		assigned_employees = self.get_assigned_employees(self.process_attendance_after, True)
		# mark absent in batches & commit to avoid losing progress since this tries to process remaining attendance
		# right from "Process Attendance After" to "Last Sync of Checkin"
		for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
			for employee in batch:
				self.mark_absent_for_dates_with_no_attendance(employee)
				self.mark_absent_for_half_day_dates(employee)

			if not frappe.in_test:
				frappe.db.commit()  # nosemgrep

	def is_half_holiday(self, employee, attendance_date):
		holiday_list = self.get_holiday_list(employee, attendance_date)
		if is_half_holiday(holiday_list, attendance_date):
			return True
		return False

	def get_employee_checkins(self) -> list[dict]:
		return frappe.get_all(
			"Employee Checkin",
			fields=[
				"name",
				"employee",
				"log_type",
				"time",
				"shift",
				"shift_start",
				"shift_end",
				"shift_actual_start",
				"shift_actual_end",
				"device_id",
				"overtime_type",
			],
			filters={
				"skip_auto_attendance": 0,
				"attendance": ("is", "not set"),
				"time": (">=", self.process_attendance_after),
				"shift_actual_end": ("<", self.last_sync_of_checkin),
				"shift": self.name,
				"offshift": 0,
			},
			order_by="employee,time",
		)

	def get_attendance(self, logs, working_hours_threshold_for_absent, working_hours_threshold_for_half_day):
		"""Return attendance_status, working_hours, late_entry, early_exit, in_time, out_time
		for a set of logs belonging to a single shift.
		Assumptions:
		1. These logs belongs to a single shift, single employee and it's not in a holiday date.
		2. Logs are in chronological order
		"""
		late_entry = early_exit = False
		total_working_hours, in_time, out_time = calculate_working_hours(
			logs, self.determine_check_in_and_check_out, self.working_hours_calculation_based_on
		)
		
		# Apply time rounding if enabled
		if cint(self.enable_time_rounding) and self.rounding_precision and in_time and out_time:
			rounded_in_time = round_time_to_precision(in_time, self.rounding_precision, 'up')
			rounded_out_time = round_time_to_precision(out_time, self.rounding_precision, 'down')
			
			# Recalculate working hours with rounded times
			if rounded_out_time > rounded_in_time:
				total_working_hours = (rounded_out_time - rounded_in_time).total_seconds() / 3600
			else:
				total_working_hours = 0
			
			# Use rounded times for late_entry/early_exit check
			in_time_for_check = rounded_in_time
			out_time_for_check = rounded_out_time
		else:
			in_time_for_check = in_time
			out_time_for_check = out_time
		
		# Apply lunch break deduction if enabled
		if cint(self.enable_lunch_deduction) and self.lunch_start and self.lunch_end and in_time and out_time:
			# Use rounded times if rounding is enabled
			check_in = rounded_in_time if cint(self.enable_time_rounding) and self.rounding_precision else in_time
			check_out = rounded_out_time if cint(self.enable_time_rounding) and self.rounding_precision else out_time
			
			lunch_overlap = calculate_lunch_overlap_hours(
				check_in, check_out, self.lunch_start, self.lunch_end
			)
			total_working_hours = max(0, total_working_hours - lunch_overlap)
		
		# Final rounding: ensure working hours is a multiple of precision (in hours)
		if cint(self.enable_time_rounding) and self.rounding_precision:
			precision_hours = int(self.rounding_precision) / 60  # e.g., 15 min = 0.25 hours
			# Round down to nearest precision unit
			total_working_hours = int(total_working_hours / precision_hours) * precision_hours
		
		# Round working hours to 2 decimal places
		total_working_hours = round(total_working_hours, 2)
		
		if (
			cint(self.enable_late_entry_marking)
			and in_time_for_check
			and in_time_for_check > logs[0].shift_start + timedelta(minutes=cint(self.late_entry_grace_period))
		):
			late_entry = True

		if (
			cint(self.enable_early_exit_marking)
			and out_time_for_check
			and out_time_for_check < logs[0].shift_end - timedelta(minutes=cint(self.early_exit_grace_period))
		):
			early_exit = True

		if working_hours_threshold_for_absent and total_working_hours < working_hours_threshold_for_absent:
			return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time

		if (
			working_hours_threshold_for_half_day
			and total_working_hours < working_hours_threshold_for_half_day
		):
			return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time

		return "Present", total_working_hours, late_entry, early_exit, in_time, out_time

	def mark_absent_for_dates_with_no_attendance(self, employee: str):
		"""Marks Absents for the given employee on working days in this shift that have no attendance marked.
		The Absent status is marked starting from 'process_attendance_after' or employee creation date.
		"""
		start_time = get_time(self.start_time)
		dates = self.get_dates_for_attendance(employee)

		for date in dates:
			timestamp = datetime.combine(date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)

			if shift_details and shift_details.shift_type.name == self.name:
				attendance = mark_attendance(employee, date, "Absent", self.name)

				if not attendance:
					continue

				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Comment",
						"reference_doctype": "Attendance",
						"reference_name": attendance,
						"content": frappe._("Employee was marked Absent due to missing Employee Checkins."),
					}
				).insert(ignore_permissions=True)

	def get_dates_for_attendance(self, employee: str) -> list[str]:
		start_date, end_date = self.get_start_and_end_dates(employee)

		# no shift assignment found, no need to process absent attendance records
		if start_date is None:
			return []

		date_range = get_date_range(start_date, end_date)

		# skip marking absent on holidays
		holiday_list = self.get_holiday_list(employee)
		holiday_dates = get_holiday_dates_between(holiday_list, start_date, end_date)
		# skip dates with attendance
		marked_attendance_dates = self.get_marked_attendance_dates_between(employee, start_date, end_date)

		return sorted(set(date_range) - set(holiday_dates) - set(marked_attendance_dates))

	def get_start_and_end_dates(self, employee):
		"""Returns start and end dates for checking attendance and marking absent
		return: start date = max of `process_attendance_after` and DOJ
		return: end date = min of shift before `last_sync_of_checkin` and Relieving Date
		"""
		date_of_joining, relieving_date, employee_creation = frappe.get_cached_value(
			"Employee", employee, ["date_of_joining", "relieving_date", "creation"]
		)

		if not date_of_joining:
			date_of_joining = employee_creation.date()

		start_date = max(getdate(self.process_attendance_after), date_of_joining)
		end_date = None

		shift_details = get_shift_details(self.name, get_datetime(self.last_sync_of_checkin))
		last_shift_time = (
			shift_details.actual_end if shift_details else get_datetime(self.last_sync_of_checkin)
		)

		# check if shift is found for 1 day before the last sync of checkin
		# absentees are auto-marked 1 day after the shift to wait for any manual attendance records
		prev_shift = get_employee_shift(employee, last_shift_time - timedelta(days=1), True, "reverse")
		if prev_shift and prev_shift.shift_type.name == self.name:
			end_date = (
				min(prev_shift.start_datetime.date(), relieving_date)
				if relieving_date
				else prev_shift.start_datetime.date()
			)
		else:
			# no shift found
			return None, None
		return start_date, end_date

	def get_marked_attendance_dates_between(self, employee: str, start_date: str, end_date: str) -> list[str]:
		Attendance = frappe.qb.DocType("Attendance")
		return (
			frappe.qb.from_(Attendance)
			.select(Attendance.attendance_date)
			.where(
				(Attendance.employee == employee)
				& (Attendance.docstatus < 2)
				& (Attendance.attendance_date.between(start_date, end_date))
				& ((Attendance.shift.isnull()) | (Attendance.shift == self.name))
			)
		).run(pluck=True)

	def get_assigned_employees(self, from_date: datetime.date, consider_default_shift=False) -> list[str]:
		"""Get all such employees who either have this shift assigned that hasn't ended or have this shift as default shift.
		This may fetch some redundant employees who have another shift assigned that may have started or ended before or after the
		attendance processing date. But this is done to avoid missing any employee who may have this shift as active shift."""
		filters = {"shift_type": self.name, "docstatus": "1", "status": "Active"}

		or_filters = [["end_date", ">=", from_date], ["end_date", "is", "not set"]]

		assigned_employees = frappe.get_all(
			"Shift Assignment", filters=filters, or_filters=or_filters, pluck="employee"
		)

		if consider_default_shift:
			default_shift_employees = frappe.get_all(
				"Employee", filters={"default_shift": self.name, "status": "Active"}, pluck="name"
			)
			assigned_employees = set(assigned_employees + default_shift_employees)

		# exclude inactive employees
		inactive_employees = frappe.db.get_all("Employee", {"status": "Inactive"}, pluck="name")

		return list(set(assigned_employees) - set(inactive_employees))

	def get_holiday_list(self, employee: str, date=None) -> str:
		holiday_list_name = self.holiday_list or get_holiday_list_for_employee(employee, False, as_on=date)
		return holiday_list_name

	def should_mark_attendance(self, employee: str, attendance_date: str) -> bool:
		"""Determines whether attendance should be marked on holidays or not"""
		if self.mark_auto_attendance_on_holidays:
			# no need to check if date is a holiday or not
			# since attendance should be marked on all days
			return True

		holiday_list = self.get_holiday_list(employee, attendance_date)
		if is_holiday(holiday_list, attendance_date):
			return False
		return True

	def mark_absent_for_half_day_dates(self, employee):
		half_day_attendances = frappe.get_all(
			"Attendance",
			filters={
				"employee": employee,
				"status": "Half Day",
				"modify_half_day_status": 1,
				"attendance_date": ["<=", getdate(self.last_sync_of_checkin)],
			},
			fields=["name", "attendance_date"],
		)
		start_time = get_time(self.start_time)
		for attendance in half_day_attendances:
			timestamp = datetime.combine(attendance.attendance_date, start_time)
			shift_details = get_employee_shift(employee, timestamp, True)
			if shift_details and shift_details.shift_type.name == self.name:
				frappe.db.set_value(
					"Attendance",
					attendance.name,
					{"shift": self.name, "half_day_status": "Absent", "modify_half_day_status": 0},
				)
				frappe.get_doc(
					{
						"doctype": "Comment",
						"comment_type": "Comment",
						"reference_doctype": "Attendance",
						"reference_name": attendance.name,
						"content": frappe._(
							"Employee was marked Absent for other half due to missing Employee Checkins."
						),
					}
				).insert(ignore_permissions=True)


def update_last_sync_of_checkin():
	"""Called from hooks"""
	shifts = frappe.get_all(
		"Shift Type",
		filters={"enable_auto_attendance": 1, "auto_update_last_sync": 1},
		fields=["name", "last_sync_of_checkin", "start_time", "end_time"],
	)
	current_datetime = frappe.flags.current_datetime or get_datetime()
	for shift in shifts:
		shift_end = get_actual_shift_end(shift, current_datetime)
		update_last_sync = None
		if shift.last_sync_of_checkin:
			if get_datetime(shift.last_sync_of_checkin) < shift_end < current_datetime:
				update_last_sync = True
		elif shift_end < current_datetime:
			update_last_sync = True
		if update_last_sync:
			frappe.db.set_value(
				"Shift Type", shift.name, "last_sync_of_checkin", shift_end + timedelta(minutes=1)
			)


def get_actual_shift_end(shift, current_datetime):
	time_within_shift = datetime.combine(current_datetime.date(), get_time(shift.start_time))
	shift_details = get_shift_details(shift.name, time_within_shift)
	actual_shift_start = shift_details["actual_start"]
	actual_shift_end = shift_details["actual_end"]

	if (actual_shift_start.date() < actual_shift_end.date()) or (current_datetime < actual_shift_start):
		# shift start and end are on different days
		actual_shift_end = add_days(actual_shift_end, -1)
	return actual_shift_end


def process_auto_attendance_for_all_shifts():
	"""Called from hooks"""
	shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
	for shift in shift_list:
		doc = frappe.get_cached_doc("Shift Type", shift)
		doc.process_auto_attendance()
