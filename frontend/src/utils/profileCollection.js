export const PROFILE_COLLECTION_STATUS = "hrms.api.employee_profile.get_collection_status"
export const PROFILE_COLLECTION_GET = "hrms.api.employee_profile.get_my_profile"
export const PROFILE_COLLECTION_SAVE = "hrms.api.employee_profile.save_my_profile"
const FIELDS = [
	"cell_number",
	"custom_wechat_id",
	"current_address",
	"contact_email",
	"person_to_be_contacted",
	"relation",
	"emergency_phone_number",
]

const COPY = {
	title: { zh: "完善个人资料", ja: "個人情報の確認", en: "Complete Your Profile" },
	lead: {
		zh: "请确认联系方式、现住址和紧急联系人",
		ja: "連絡先・現住所・緊急連絡先を確認してください",
		en: "Confirm your contact details, current address and emergency contact",
	},
	entryLead: {
		zh: "填写或更新联系方式和紧急联系人",
		ja: "連絡先と緊急連絡先を入力・更新",
		en: "Add or update your contact and emergency contact details",
	},
	entryAction: { zh: "去填写", ja: "入力する", en: "Complete" },
	name: { zh: "姓名", ja: "氏名", en: "Name" },
	number: { zh: "员工编号", ja: "従業員番号", en: "Employee ID" },
	cell_number: { zh: "手机号", ja: "携帯電話番号", en: "Mobile Number" },
	custom_wechat_id: { zh: "微信号（选填）", ja: "WeChat ID（任意）", en: "WeChat ID (optional)" },
	wechatHint: {
		zh: "没有微信可留空，请填写微信号而非昵称。",
		ja: "未使用の場合は空欄可。表示名ではなくIDを入力してください。",
		en: "Leave blank if you do not use WeChat. Enter your ID, not your display name.",
	},
	contact_email: { zh: "联系邮箱", ja: "連絡用メールアドレス", en: "Contact Email" },
	emailHint: {
		zh: "用于联系，不会修改你的登录账号。",
		ja: "連絡用です。ログインアカウントは変更されません。",
		en: "For contacting you. Your login account stays the same.",
	},
	current_address: { zh: "现住址", ja: "現住所", en: "Current Address" },
	emergencyTitle: { zh: "紧急联系人", ja: "緊急連絡先", en: "Emergency Contact" },
	person_to_be_contacted: {
		zh: "紧急联系人姓名",
		ja: "緊急連絡先の氏名",
		en: "Emergency Contact Name",
	},
	relation: { zh: "亲属", ja: "親族", en: "Relative" },
	emergency_phone_number: {
		zh: "紧急联系电话",
		ja: "緊急連絡先の電話番号",
		en: "Emergency Contact Phone",
	},
	relationHint: {
		zh: "例如：父母、配偶、子女。",
		ja: "例：父母・配偶者・子ども。",
		en: "For example: parent, spouse or child.",
	},
	emergencyPhoneHint: {
		zh: "请填写可直接联系到对方的电话，支持国家区号。",
		ja: "直接連絡できる電話番号を入力してください。国番号も使えます。",
		en: "Enter a phone number where they can be reached directly, including a country code if needed.",
	},
	addressHint: {
		zh: "请填写到门牌、楼栋和房间号。",
		ja: "番地・建物名・部屋番号まで入力してください。",
		en: "Include the street, building and apartment number.",
	},
	required: {
		zh: "请填写此项。",
		ja: "この項目を入力してください。",
		en: "Please fill in this field.",
	},
	invalidEmail: {
		zh: "请输入有效的邮箱地址。",
		ja: "有効なメールアドレスを入力してください。",
		en: "Enter a valid email address.",
	},
	submit: { zh: "确认并提交", ja: "確認して送信", en: "Confirm and Submit" },
	submitting: { zh: "正在提交…", ja: "送信中…", en: "Submitting…" },
	loading: { zh: "正在读取你的资料…", ja: "情報を読み込み中…", en: "Loading your profile…" },
	loadFailed: {
		zh: "暂时无法读取资料，请重试。",
		ja: "情報を読み込めません。再試行してください。",
		en: "Could not load your profile. Please try again.",
	},
	saveFailed: {
		zh: "提交未成功，填写内容已保留，请重试。",
		ja: "送信できませんでした。入力内容は保持されています。再試行してください。",
		en: "Your changes were not submitted. They are still here; please try again.",
	},
	unavailable: {
		zh: "当前账号暂未开放此功能。",
		ja: "このアカウントではまだ利用できません。",
		en: "This feature is not enabled for your account yet.",
	},
	conflict: {
		zh: "资料已被更新，请重新读取后再确认提交。",
		ja: "情報が更新されています。再読み込みして確認してください。",
		en: "Your profile has changed. Reload it before submitting again.",
	},
	reload: { zh: "重新读取资料", ja: "情報を再読み込み", en: "Reload Profile" },
	retry: { zh: "重试", ja: "再試行", en: "Try Again" },
	success: { zh: "提交成功", ja: "送信完了", en: "Submitted" },
	successLead: {
		zh: "你的资料已更新，HR 可在员工信息总表中查看。",
		ja: "情報を更新しました。人事担当者の従業員一覧に反映されます。",
		en: "Your profile has been updated and is available to HR in the employee overview.",
	},
	home: { zh: "返回首页", ja: "ホームに戻る", en: "Back to Home" },
	editAgain: { zh: "修改我的资料", ja: "自分の情報を編集", en: "Edit My Profile" },
}

export function profileCollectionCopy(key, lang = "zh") {
	return COPY[key]?.[lang] || COPY[key]?.zh || key
}

export function profileFormValues(profile = {}) {
	return Object.fromEntries(FIELDS.map((field) => [field, profile[field] || ""]))
}

export function validateProfileForm(values) {
	const errors = {}
	for (const field of [
		"cell_number",
		"current_address",
		"contact_email",
		"person_to_be_contacted",
		"relation",
		"emergency_phone_number",
	]) {
		if (!String(values[field] || "").trim()) errors[field] = "required"
	}
	if (!errors.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.contact_email.trim())) {
		errors.contact_email = "invalidEmail"
	}
	return errors
}

export function profileSubmission(profile, values) {
	return {
		...Object.fromEntries(FIELDS.map((field) => [field, String(values[field] || "").trim()])),
		modified: profile.modified,
	}
}
