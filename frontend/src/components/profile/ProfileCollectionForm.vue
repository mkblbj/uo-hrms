<template>
	<form
		class="profile-collection-form"
		novalidate
		:aria-busy="submitting"
		@submit.prevent="submit"
	>
		<dl class="profile-identity">
			<div>
				<dt>{{ t("name") }}</dt>
				<dd>{{ profile.employee_name }}</dd>
			</div>
			<div>
				<dt>{{ t("number") }}</dt>
				<dd>{{ profile.employee_number }}</dd>
			</div>
		</dl>
		<div v-for="field in fields" :key="field.name" class="profile-field">
			<h3 v-if="field.name === 'person_to_be_contacted'" class="profile-emergency-heading">
				{{ t("emergencyTitle") }}
			</h3>
			<label :for="`profile-${field.name}`"
				>{{ t(field.name)
				}}<span v-if="field.required" class="required" aria-hidden="true"> *</span></label
			>
			<textarea
				v-if="field.name === 'current_address'"
				:id="`profile-${field.name}`"
				v-model="form[field.name]"
				:name="field.name"
				autocomplete="street-address"
				rows="3"
				required
				:disabled="submitting"
				:aria-invalid="Boolean(errors[field.name])"
				:aria-describedby="`profile-help-${field.name}`"
				@blur="validateField(field.name)"
			/>
			<input
				v-else
				:id="`profile-${field.name}`"
				v-model="form[field.name]"
				:name="field.name"
				:type="field.type"
				:autocomplete="field.autocomplete"
				:required="field.required"
				maxlength="140"
				:disabled="submitting"
				:aria-invalid="Boolean(errors[field.name])"
				:aria-describedby="`profile-help-${field.name}`"
				@blur="validateField(field.name)"
			/>
			<div :id="`profile-help-${field.name}`" class="profile-field-help">
				<p v-if="errors[field.name]" class="profile-field-error" role="alert">
					{{ t(errors[field.name]) }}
				</p>
				<p v-else-if="field.hint">{{ t(field.hint) }}</p>
			</div>
		</div>
		<p v-if="error" class="profile-submit-error" role="alert">{{ error }}</p>
		<div class="profile-submit-bar">
			<button type="submit" class="profile-submit" :disabled="submitting">
				{{ t(submitting ? "submitting" : "submit") }}
			</button>
		</div>
	</form>
</template>

<script setup>
import { reactive, watch } from "vue"
import {
	profileCollectionCopy,
	profileFormValues,
	validateProfileForm,
} from "@/utils/profileCollection"

const props = defineProps({
	profile: { type: Object, required: true },
	lang: { type: String, default: "zh" },
	submitting: { type: Boolean, default: false },
	error: { type: String, default: "" },
})
const emit = defineEmits(["submit"])
const t = (key) => profileCollectionCopy(key, props.lang)
const form = reactive(profileFormValues(props.profile))
const errors = reactive({})
const fields = [
	{ name: "cell_number", type: "tel", autocomplete: "tel", required: true },
	{
		name: "custom_wechat_id",
		type: "text",
		autocomplete: "off",
		required: false,
		hint: "wechatHint",
	},
	{
		name: "contact_email",
		type: "email",
		autocomplete: "email",
		required: true,
		hint: "emailHint",
	},
	{ name: "current_address", required: true, hint: "addressHint" },
	{ name: "person_to_be_contacted", type: "text", autocomplete: "off", required: true },
	{ name: "relation", type: "text", autocomplete: "off", required: true, hint: "relationHint" },
	{
		name: "emergency_phone_number",
		type: "tel",
		autocomplete: "off",
		required: true,
		hint: "emergencyPhoneHint",
	},
]
watch(
	() => props.profile,
	(profile) => {
		Object.assign(form, profileFormValues(profile))
		for (const field in errors) delete errors[field]
	}
)
function validateField(field) {
	const next = validateProfileForm(form)
	if (next[field]) errors[field] = next[field]
	else delete errors[field]
}
function submit() {
	if (props.submitting) return
	for (const field in errors) delete errors[field]
	Object.assign(errors, validateProfileForm(form))
	if (!Object.keys(errors).length) emit("submit", { ...form })
}
</script>

<style scoped>
.profile-collection-form {
	display: flex;
	flex-direction: column;
	gap: 20px;
}
.profile-identity {
	margin: 0 0 2px;
	padding: 16px;
	border-radius: 12px;
	background: var(--h-bg-page, #f1eee7);
}
.profile-identity div {
	display: grid;
	grid-template-columns: 85px 1fr;
	gap: 12px;
	padding: 5px 0;
}
.profile-identity dt {
	color: var(--h-fg-secondary, #64706a);
	font-size: 14px;
}
.profile-identity dd {
	margin: 0;
	color: var(--h-fg-primary, #161b1a);
	font-size: 15px;
	overflow-wrap: anywhere;
}
.profile-field label {
	display: block;
	margin-bottom: 9px;
	font-size: 15px;
	font-weight: 600;
	color: var(--h-fg-primary, #161b1a);
}
.profile-emergency-heading {
	margin: 6px 0 22px;
	padding-top: 22px;
	border-top: 1px solid var(--h-bd-default, #e3dfd4);
	color: var(--h-fg-primary, #161b1a);
	font-size: 18px;
	font-weight: 650;
}
.required {
	color: #9b4141;
}
.profile-field input,
.profile-field textarea {
	display: block;
	width: 100%;
	min-height: 48px;
	padding: 12px 13px;
	border: 1px solid var(--h-bd-default, #dcded8);
	border-radius: 10px;
	background: var(--h-bg-elevated, #fff);
	color: var(--h-fg-primary, #161b1a);
	font: inherit;
	font-size: 16px;
	line-height: 1.5;
}
.profile-field textarea {
	resize: vertical;
}
.profile-field input:focus,
.profile-field textarea:focus {
	outline: 2px solid #23755b;
	outline-offset: 2px;
}
.profile-field [aria-invalid="true"] {
	border-color: #a84545;
}
.profile-field-help p {
	margin: 7px 0 0;
	font-size: 13px;
	line-height: 1.6;
	color: var(--h-fg-secondary, #64706a);
}
.profile-field-help .profile-field-error,
.profile-submit-error {
	color: #a43e3e;
}
.profile-submit-error {
	font-size: 14px;
	line-height: 1.6;
}
.profile-submit-bar {
	padding-top: 4px;
	padding-bottom: env(safe-area-inset-bottom, 0px);
}
.profile-submit {
	width: 100%;
	min-height: 50px;
	padding: 13px 18px;
	border: 0;
	border-radius: 11px;
	background: #23755b;
	color: #fff;
	font: inherit;
	font-size: 16px;
	font-weight: 600;
	cursor: pointer;
}
.profile-submit:focus-visible {
	outline: 2px solid #23755b;
	outline-offset: 3px;
}
.profile-submit:disabled,
.profile-field :disabled {
	cursor: wait;
	opacity: 0.65;
}
</style>
