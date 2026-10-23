"""员工头像：照片处理、谁能看到、离职删除。

照片存成公开文件（文件名随机），墙上屏和看板不用登录也能显示；
所以不登录的接口只在公司网络、或墙上屏带着有效展示密钥时才返回头像地址。
"""

import io
import math

from PIL import Image, ImageOps, ImageSequence

import frappe
from frappe import _
from frappe.utils import cint

from hrms.utils.client_network import get_client_ip, is_office_network

PHOTO_FIELD = "image"
PHOTO_FILE_PREFIX = "profile-photo-"
PHOTO_MAX_SIDE = 512
PHOTO_MIN_SIDE = 128
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000


def normalize_photo(content: bytes, crop: dict | None = None) -> bytes:
	"""裁成最大 512 的正方形，去掉元数据；GIF 保留动画，其他照片保存为 JPEG。"""
	if not content:
		frappe.throw(_("Please choose a photo."))
	if len(content) > MAX_UPLOAD_BYTES:
		frappe.throw(_("This photo is too large. Please choose one under 10 MB."))

	image = _decode(content)
	side = min(image.size)
	if side < PHOTO_MIN_SIDE:
		frappe.throw(_("This photo is too small. Please choose a clearer one."))

	box = _crop_box(image, crop)
	if image.format == "GIF":
		return _normalize_gif(image, box)
	image = _normalize_frame(image, box)

	output = io.BytesIO()
	image.save(output, format="JPEG", quality=88, optimize=True)
	return output.getvalue()


def _crop_box(image: Image.Image, crop: dict | None) -> tuple[int, int, int, int]:
	if crop is None:
		size = min(image.size)
		left = (image.width - size) // 2
		top = (image.height - size) // 2
	else:
		invalid_crop = _("This photo could not be cropped. Please choose it again.")
		try:
			left, top, size = (float(crop[key]) for key in ("sx", "sy", "size"))
		except (KeyError, TypeError, ValueError):
			frappe.throw(invalid_crop)
		if (
			not all(math.isfinite(value) for value in (left, top, size))
			or min(left, top) < 0
			or size < PHOTO_MIN_SIDE
			or left + size > image.width
			or top + size > image.height
		):
			frappe.throw(invalid_crop)
		size = round(size)
		left = min(round(left), image.width - size)
		top = min(round(top), image.height - size)
	return (left, top, left + size, top + size)


def _normalize_frame(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
	image = _flatten(image).crop(box)
	side = box[2] - box[0]
	if side > PHOTO_MAX_SIDE:
		image = image.resize((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), Image.Resampling.LANCZOS)
	image.info.clear()
	return image


def _normalize_gif(image: Image.Image, box: tuple[int, int, int, int]) -> bytes:
	try:
		# 动图按所有帧的总像素计算，沿用原来的解码预算。
		if image.width * image.height * image.n_frames > MAX_SOURCE_PIXELS:
			frappe.throw(_("This photo is too large. Please choose a smaller one."))
		loop = image.info.get("loop")
		frames = []
		durations = []
		for frame in ImageSequence.Iterator(image):
			durations.append(frame.info.get("duration", 0))
			# Pillow 会合成局部帧及其背景；裁剪的是每一帧实际显示的画面。
			frames.append(_normalize_frame(frame, box))
		output = io.BytesIO()
		frames[0].save(
			output,
			format="GIF",
			save_all=True,
			append_images=frames[1:],
			duration=durations,
			disposal=2,
			optimize=True,
			**({"loop": loop} if loop is not None else {}),
		)
		return output.getvalue()
	except (OSError, ValueError, EOFError):
		frappe.throw(_("This file could not be read as a photo. Please choose another one."))


def _decode(content: bytes) -> Image.Image:
	"""先只读尺寸，像素太多就不解码，免得撑爆内存。"""
	unreadable = _("This file could not be read as a photo. Please choose another one.")
	too_large = _("This photo is too large. Please choose a smaller one.")
	try:
		image = Image.open(io.BytesIO(content))
	except Image.DecompressionBombError:
		frappe.throw(too_large)
	except Exception:
		frappe.throw(unreadable)

	if image.width * image.height > MAX_SOURCE_PIXELS:
		frappe.throw(too_large)

	try:
		if image.format != "GIF":
			image = ImageOps.exif_transpose(image)
		image.load()
	except Exception:
		frappe.throw(unreadable)
	return image


def _flatten(image: Image.Image) -> Image.Image:
	"""透明部分铺白底，统一成 RGB。"""
	if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
		image = image.convert("RGBA")
		background = Image.new("RGB", image.size, (255, 255, 255))
		background.paste(image, mask=image.getchannel("A"))
		return background
	return image.convert("RGB")


def can_see_photos(location: str | None = None, key: str | None = None) -> bool:
	"""登录用户都能看到头像；不登录的只有公司网络、或带着必需且正确的展示密钥才行。"""
	if frappe.session.user != "Guest":
		return True
	if is_office_network(get_client_ip()):
		return True
	if not (location and key):
		return False

	from hrms.hr.doctype.qr_checkin_location.qr_checkin_location import verify_display_key

	requires_key = cint(frappe.db.get_value("QR Checkin Location", location, "require_display_key"))
	return bool(requires_key) and verify_display_key(location, key)


def photo_set_by_employee(employee) -> bool:
	"""员工自己在应用里上传的头像才算设好；HR 或脚本替他设的算临时头像。"""
	if not (employee.image and employee.user_id):
		return False
	return bool(
		frappe.db.exists(
			"File",
			{
				"attached_to_doctype": "Employee",
				"attached_to_name": employee.name,
				"attached_to_field": PHOTO_FIELD,
				"file_url": employee.image,
				"owner": employee.user_id,
			},
		)
	)


def delete_photo_files(
	employee: str, user: str | None = None, keep_url: str | None = None, keep_name: str | None = None
) -> None:
	"""删掉旧头像的文件记录：员工头像字段上的，和账号头像字段上的。

	保存账号时，框架会把头像图片再挂一份到账号上，不一起删，旧照片就还留在磁盘上。
	keep_name 指定时，员工字段上只留这一条（顺便去掉同图的重复记录）；否则留下地址等于 keep_url 的。
	别处还在用同一份文件时，磁盘上的会保留。
	"""
	targets = [("Employee", employee, PHOTO_FIELD)]
	if user:
		targets.append(("User", user, "user_image"))
		if "raven" in frappe.get_installed_apps():
			targets.append(("Raven User", user, "user_image"))
	for doctype, name, field in targets:
		rows = frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": name, "attached_to_field": field},
			fields=["name", "file_url"],
		)
		for row in rows:
			if doctype == "Employee" and keep_name:
				keep = row.name == keep_name
			else:
				keep = bool(keep_url) and row.file_url == keep_url
			if not keep:
				frappe.delete_doc("File", row.name, ignore_permissions=True)


def sync_profile_photo(doc, method=None):
	"""Employee on_update：离职就删头像；HR 在后台换掉或清空头像时，同步账号头像并删掉旧文件。"""
	if doc.status == "Left":
		if doc.image:
			_remove_departed_photo(doc)
		return

	before = doc.get_doc_before_save()
	if not before or before.image == doc.image:
		return
	if doc.user_id:
		frappe.db.set_value("User", doc.user_id, "user_image", doc.image or None)
		frappe.clear_cache(user=doc.user_id)
		sync_raven_profile_photo(doc.user_id, doc.image)
	delete_photo_files(doc.name, doc.user_id, keep_url=doc.image)


def _remove_departed_photo(doc) -> None:
	try:
		frappe.db.set_value("Employee", doc.name, PHOTO_FIELD, None, update_modified=False)
		doc.image = None
		if doc.user_id:
			frappe.db.set_value("User", doc.user_id, "user_image", None, update_modified=False)
			frappe.clear_cache(user=doc.user_id)
			sync_raven_profile_photo(doc.user_id, None)
		delete_photo_files(doc.name, doc.user_id)
	except Exception:
		frappe.log_error(
			title="Profile photo cleanup failed", reference_doctype="Employee", reference_name=doc.name
		)


def sync_raven_profile_photo(user: str, photo: str | None) -> None:
	"""让 Raven 使用账号头像，并通过原生保存流程更新文件关联、缓存和实时通知。"""
	if "raven" not in frappe.get_installed_apps() or not frappe.db.exists("Raven User", user):
		return
	raven_user = frappe.get_doc("Raven User", user)
	if (raven_user.user_image or None) == (photo or None):
		return
	raven_user.user_image = photo or None
	raven_user.save(ignore_permissions=True)


def sync_user_photo_to_raven(doc, method=None) -> None:
	before = doc.get_doc_before_save()
	if before and before.user_image != doc.user_image:
		sync_raven_profile_photo(doc.name, doc.user_image)
