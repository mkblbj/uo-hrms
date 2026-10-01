import io
import os
from unittest.mock import patch

from PIL import Image
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

import frappe
from frappe.utils import add_days, now_datetime, today

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import profile_photo as api
from hrms.api import qr_attendance
from hrms.tests.utils import HRMSTestSuite
from hrms.utils import profile_photo

PHOTO_USER = "profile-photo@example.com"
OTHER_USER = "profile-photo-other@example.com"
LOCATION = "profile-photo-door"
OFFICE_NETWORK = "192.0.2.0/24"
OFFICE_IP = "192.0.2.10"
OUTSIDE_IP = "203.0.113.9"


def make_image(size=(800, 600), color=(200, 30, 30), fmt="JPEG", mode="RGB", exif=None, split_at=None):
	image = Image.new(mode, size, color)
	if split_at:
		image.paste((30, 30, 200), (split_at, 0, size[0], size[1]))
	buffer = io.BytesIO()
	image.save(buffer, format=fmt, **({"exif": exif} if exif else {}))
	return buffer.getvalue()


def photo_files(employee):
	return frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Employee",
			"attached_to_name": employee,
			"attached_to_field": "image",
		},
		pluck="file_url",
	)


class TestNormalizePhoto(HRMSTestSuite):
	def test_outputs_square_jpeg_capped_at_512(self):
		image = Image.open(io.BytesIO(profile_photo.normalize_photo(make_image((2000, 1200)))))
		self.assertEqual(image.format, "JPEG")
		self.assertEqual(image.size, (512, 512))

	def test_small_photo_is_cropped_but_not_enlarged(self):
		image = Image.open(io.BytesIO(profile_photo.normalize_photo(make_image((400, 300)))))
		self.assertEqual(image.size, (300, 300))

	def test_applies_exif_orientation_and_drops_all_metadata(self):
		exif = Image.Exif()
		exif[0x0112] = 6  # 显示时要顺时针转 90 度
		exif[0x010F] = "Test Phone"
		# 左边 100 像素红、其余蓝；转正后红色在上面
		source = make_image((400, 300), color=(220, 20, 20), exif=exif.tobytes(), split_at=100)
		image = Image.open(io.BytesIO(profile_photo.normalize_photo(source)))
		self.assertEqual(len(image.getexif()), 0)
		self.assertNotIn("exif", image.info)
		top, bottom = image.getpixel((150, 10)), image.getpixel((150, 290))
		self.assertGreater(top[0], 150)
		self.assertLess(top[2], 100)
		self.assertLess(bottom[0], 100)
		self.assertGreater(bottom[2], 150)

	def test_flattens_transparency_onto_white(self):
		png = make_image((300, 300), color=(0, 0, 0, 0), fmt="PNG", mode="RGBA")
		image = Image.open(io.BytesIO(profile_photo.normalize_photo(png)))
		self.assertEqual(image.mode, "RGB")
		self.assertGreater(min(image.getpixel((150, 150))), 240)

	def test_rejects_files_that_are_not_images(self):
		with self.assertRaises(frappe.ValidationError):
			profile_photo.normalize_photo(b"not an image at all")

	def test_rejects_empty_uploads(self):
		with self.assertRaises(frappe.ValidationError):
			profile_photo.normalize_photo(b"")

	def test_rejects_tiny_images(self):
		with self.assertRaises(frappe.ValidationError):
			profile_photo.normalize_photo(make_image((100, 400)))

	def test_rejects_oversized_uploads(self):
		with self.assertRaises(frappe.ValidationError):
			profile_photo.normalize_photo(b"x" * (profile_photo.MAX_UPLOAD_BYTES + 1))

	def test_rejects_images_with_too_many_pixels(self):
		with patch.object(profile_photo, "MAX_SOURCE_PIXELS", 1000):
			with self.assertRaises(frappe.ValidationError):
				profile_photo.normalize_photo(make_image((200, 200)))


class ProfilePhotoTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(PHOTO_USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for employee, user in ((self.employee, PHOTO_USER), (self.other_employee, OTHER_USER)):
			frappe.get_doc("User", user).add_roles("Employee")
			frappe.db.set_value(
				"Employee", employee, {"image": None, "status": "Active", "relieving_date": None}
			)
			frappe.db.set_value("User", user, "user_image", None)
			frappe.db.delete("File", {"attached_to_doctype": "Employee", "attached_to_name": employee})
		frappe.db.set_single_value(
			"HR Settings", {"require_profile_photo": 0, "profile_photo_deadline": None}
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def upload(self, content, user=PHOTO_USER):
		frappe.set_user(user)
		try:
			return api.save_employee_photo(api.get_current_employee(), content)
		finally:
			frappe.set_user("Administrator")


class TestUploadMyPhoto(ProfilePhotoTestCase):
	def test_raven_avatar_follows_employee_upload_replace_and_clear(self):
		if "raven" not in frappe.get_installed_apps():
			self.skipTest("Raven is optional")
		frappe.get_doc("User", PHOTO_USER).add_roles("Raven User")
		from raven.api.raven_users import get_users

		get_users()  # Seed the cache before the photo changes.
		first = self.upload(make_image(color=(20, 180, 20)))["photo"]
		self.assertEqual(frappe.db.get_value("Raven User", PHOTO_USER, "user_image"), first)
		second = self.upload(make_image(color=(20, 20, 180)))["photo"]
		self.assertNotEqual(first, second)
		self.assertEqual(next(user for user in get_users() if user.name == PHOTO_USER).user_image, second)
		employee = frappe.get_doc("Employee", self.employee)
		employee.image = None
		employee.save()
		self.assertFalse(frappe.db.get_value("Raven User", PHOTO_USER, "user_image"))

	def test_sets_employee_and_account_photo_from_a_public_random_file(self):
		url = self.upload(make_image((1000, 800)))["photo"]
		self.assertRegex(url, r"^/files/profile-photo-[0-9a-f]{20}\.jpg$")
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "image"), url)
		self.assertEqual(frappe.db.get_value("User", PHOTO_USER, "user_image"), url)
		file = frappe.get_doc("File", {"file_url": url})
		self.assertEqual(file.is_private, 0)
		self.assertEqual(photo_files(self.employee), [url])
		with open(file.get_full_path(), "rb") as handle:
			self.assertEqual(Image.open(handle).size, (512, 512))

	def test_replacing_the_photo_deletes_the_previous_file(self):
		first = self.upload(make_image((600, 600), color=(10, 200, 10)))["photo"]
		first_path = frappe.get_doc("File", {"file_url": first}).get_full_path()
		second = self.upload(make_image((600, 600), color=(10, 10, 200)))["photo"]
		self.assertNotEqual(first, second)
		self.assertEqual(photo_files(self.employee), [second])
		self.assertFalse(os.path.exists(first_path))

	def test_replacing_also_removes_the_copy_attached_to_the_account(self):
		first = self.upload(make_image((600, 600), color=(10, 200, 10)))["photo"]
		first_path = frappe.get_doc("File", {"file_url": first}).get_full_path()
		# 保存账号时框架会把头像再挂一份到账号上
		frappe.get_doc("User", PHOTO_USER).save(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("File", {"attached_to_doctype": "User", "file_url": first}))
		self.upload(make_image((600, 600), color=(10, 10, 200)))
		self.assertFalse(frappe.db.exists("File", {"file_url": first}))
		self.assertFalse(os.path.exists(first_path))

	def test_uploading_the_same_photo_twice_keeps_the_file_on_disk(self):
		data = make_image((600, 600))
		self.upload(data)
		second = self.upload(data)["photo"]
		self.assertEqual(photo_files(self.employee), [second])
		self.assertTrue(os.path.exists(frappe.get_doc("File", {"file_url": second}).get_full_path()))
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "image"), second)

	def test_only_active_employees_can_upload(self):
		frappe.db.set_value("Employee", self.employee, "status", "Inactive")
		frappe.set_user(PHOTO_USER)
		with self.assertRaises(frappe.PermissionError):
			api.get_current_employee()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			api.get_current_employee()

	def test_endpoint_is_post_only_and_reads_the_file_field(self):
		self.assertEqual(
			list(frappe.allowed_http_methods_for_whitelisted_func[api.upload_my_photo]), ["POST"]
		)
		body = {"file": (io.BytesIO(make_image((300, 300))), "photo.jpg", "image/jpeg")}
		request = Request(EnvironBuilder(method="POST", data=body).get_environ())
		frappe.set_user(PHOTO_USER)
		with patch.object(frappe.local, "request", request, create=True):
			url = api.upload_my_photo()["photo"]
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "image"), url)

	def test_endpoint_requires_a_file(self):
		request = Request(EnvironBuilder(method="POST", data={"other": "x"}).get_environ())
		frappe.set_user(PHOTO_USER)
		with patch.object(frappe.local, "request", request, create=True):
			with self.assertRaises(frappe.ValidationError):
				api.upload_my_photo()


class TestProfilePhotoStatus(ProfilePhotoTestCase):
	def status(self):
		frappe.set_user(PHOTO_USER)
		try:
			return api.get_profile_photo_status()
		finally:
			frappe.set_user("Administrator")

	def test_off_by_default(self):
		self.assertEqual(
			self.status(),
			{
				"required": False,
				"has_photo": False,
				"temporary": False,
				"photo": None,
				"deadline": None,
				"overdue": False,
			},
		)

	def test_reports_deadline_and_overdue(self):
		yesterday = add_days(today(), -1)
		frappe.db.set_single_value(
			"HR Settings", {"require_profile_photo": 1, "profile_photo_deadline": yesterday}
		)
		status = self.status()
		self.assertTrue(status["required"])
		self.assertEqual(status["deadline"], str(yesterday))
		self.assertTrue(status["overdue"])

	def test_not_overdue_on_the_deadline_day(self):
		frappe.db.set_single_value(
			"HR Settings", {"require_profile_photo": 1, "profile_photo_deadline": today()}
		)
		self.assertFalse(self.status()["overdue"])

	def test_reports_the_uploaded_photo(self):
		url = self.upload(make_image((300, 300)))["photo"]
		status = self.status()
		self.assertTrue(status["has_photo"])
		self.assertFalse(status["temporary"])
		self.assertEqual(status["photo"], url)

	def set_photo_as(self, owner):
		# 模拟 HR 或脚本替员工设的头像：文件由别人上传、挂在员工头像字段上
		frappe.set_user(owner)
		try:
			file = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "landscape-avatar-test.png",
					"content": make_image((256, 256), fmt="PNG"),
					"is_private": 0,
					"attached_to_doctype": "Employee",
					"attached_to_name": self.employee,
					"attached_to_field": "image",
				}
			).insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		frappe.db.set_value("Employee", self.employee, "image", file.file_url)
		frappe.db.set_value("User", PHOTO_USER, "user_image", file.file_url)
		return file.file_url

	def test_photo_set_by_someone_else_is_temporary(self):
		url = self.set_photo_as("Administrator")
		status = self.status()
		self.assertFalse(status["has_photo"])
		self.assertTrue(status["temporary"])
		self.assertEqual(status["photo"], url)

	def test_uploading_replaces_the_temporary_photo(self):
		temporary = self.set_photo_as("Administrator")
		url = self.upload(make_image((300, 300)))["photo"]
		status = self.status()
		self.assertTrue(status["has_photo"])
		self.assertFalse(status["temporary"])
		self.assertEqual(photo_files(self.employee), [url])
		self.assertFalse(frappe.db.exists("File", {"file_url": temporary}))


class TestEmployeePhotoSync(ProfilePhotoTestCase):
	def test_hr_changing_the_employee_photo_updates_the_account_photo(self):
		url = (
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "hr-upload.jpg",
					"content": make_image((300, 300)),
					"is_private": 0,
				}
			)
			.insert()
			.file_url
		)
		doc = frappe.get_doc("Employee", self.employee)
		doc.image = url
		doc.save()
		self.assertEqual(frappe.db.get_value("User", PHOTO_USER, "user_image"), url)
		doc.reload()
		doc.image = None
		doc.save()
		self.assertFalse(frappe.db.get_value("User", PHOTO_USER, "user_image"))

	def test_hr_clearing_the_photo_deletes_its_files(self):
		url = self.upload(make_image((600, 600), color=(120, 120, 20)))["photo"]
		path = frappe.get_doc("File", {"file_url": url}).get_full_path()
		frappe.get_doc("User", PHOTO_USER).save(ignore_permissions=True)
		doc = frappe.get_doc("Employee", self.employee)
		doc.image = None
		doc.save()
		self.assertFalse(frappe.db.exists("File", {"file_url": url}))
		self.assertFalse(os.path.exists(path))
		self.assertFalse(frappe.db.get_value("User", PHOTO_USER, "user_image"))

	def test_saving_other_fields_leaves_the_account_photo_alone(self):
		frappe.db.set_value("User", PHOTO_USER, "user_image", "/files/own-choice.jpg")
		doc = frappe.get_doc("Employee", self.employee)
		doc.cell_number = "0000"
		doc.save()
		self.assertEqual(frappe.db.get_value("User", PHOTO_USER, "user_image"), "/files/own-choice.jpg")

	def test_leaving_deletes_the_photo(self):
		url = self.upload(make_image((600, 600)))["photo"]
		path = frappe.get_doc("File", {"file_url": url}).get_full_path()
		doc = frappe.get_doc("Employee", self.employee)
		doc.status = "Left"
		doc.relieving_date = today()
		doc.save()
		self.assertFalse(frappe.db.get_value("Employee", self.employee, "image"))
		self.assertFalse(frappe.db.get_value("User", PHOTO_USER, "user_image"))
		self.assertEqual(photo_files(self.employee), [])
		self.assertFalse(os.path.exists(path))


class TestGuestPhotoVisibility(ProfilePhotoTestCase):
	def setUp(self):
		super().setUp()
		if not frappe.db.exists("QR Checkin Location", LOCATION):
			frappe.get_doc(
				{"doctype": "QR Checkin Location", "location_name": LOCATION, "secret": "p" * 32}
			).insert()
		frappe.db.set_value("QR Checkin Location", LOCATION, "require_display_key", 0)
		self.key = frappe.get_doc("QR Checkin Location", LOCATION).get_password("display_key")
		frappe.db.set_single_value("HR Settings", "qr_checkin_allowed_ips", OFFICE_NETWORK)
		frappe.db.delete("Employee Checkin", {"employee": self.employee})
		self.photo = self.upload(make_image((300, 300)))["photo"]
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"log_type": "IN",
				"time": now_datetime(),
				"device_id": LOCATION,
			}
		).insert()

	def fetch(self, user="Guest", ip=OUTSIDE_IP, key=None):
		frappe.set_user(user)
		try:
			with patch("hrms.utils.profile_photo.get_client_ip", return_value=ip):
				recent = qr_attendance.get_recent_checkins(location=LOCATION, limit=1, key=key)
				at_work = qr_attendance.get_employees_at_work(location=LOCATION, key=key)
		finally:
			frappe.set_user("Administrator")
		mine = [row for row in at_work["employees"] if row["employee"] == self.employee]
		return recent[0]["employee_image"], mine[0]["image"]

	def test_guest_outside_the_office_gets_no_photo(self):
		self.assertEqual(self.fetch(), (None, None))

	def test_guest_on_the_office_network_gets_the_photo(self):
		self.assertEqual(self.fetch(ip=OFFICE_IP), (self.photo, self.photo))

	def test_wall_display_needs_a_required_and_valid_key(self):
		self.assertEqual(self.fetch(key=self.key), (None, None))
		frappe.db.set_value("QR Checkin Location", LOCATION, "require_display_key", 1)
		self.assertEqual(self.fetch(key="wrong"), (None, None))
		self.assertEqual(self.fetch(key=self.key), (self.photo, self.photo))

	def test_signed_in_users_get_the_photo(self):
		self.assertEqual(self.fetch(user=OTHER_USER), (self.photo, self.photo))
