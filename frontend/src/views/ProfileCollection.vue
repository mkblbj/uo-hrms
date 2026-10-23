<template>
	<BaseLayout :page-title="t(submitted ? 'success' : 'title')" back-route="/profile">
		<template #body>
			<main class="profile-collection-page">
				<div v-if="loading" class="profile-state" role="status">{{ t("loading") }}</div>
				<section v-else-if="!profile" class="profile-state">
					<p role="alert">{{ loadError }}</p>
					<button v-if="!unavailable" class="profile-secondary" @click="load">
						{{ t("retry") }}
					</button>
					<router-link :to="{ name: 'Home' }" class="profile-home-link">{{
						t("home")
					}}</router-link>
				</section>
				<section v-else-if="submitted" class="profile-success" aria-live="polite">
					<div class="profile-success-icon" aria-hidden="true">
						<Icon icon="lucide-check" class="h-12 w-12" />
					</div>
					<h1>{{ t("success") }}</h1>
					<p class="profile-success-lead">{{ t("successLead") }}</p>
					<dl class="profile-success-summary">
						<div>
							<dt>{{ t("name") }}</dt>
							<dd>{{ profile.employee_name }}</dd>
						</div>
						<div v-for="field in summaryFields" :key="field">
							<dt>{{ t(field) }}</dt>
							<dd>{{ profile[field] || "—" }}</dd>
						</div>
					</dl>
					<router-link :to="{ name: 'Home' }" class="profile-primary">{{ t("home") }}</router-link>
					<button class="profile-edit-again" @click="submitted = false">
						{{ t("editAgain") }}
					</button>
				</section>
				<section v-else class="profile-form-card">
					<div class="profile-form-lead">
						<Icon icon="lucide-info" class="h-5 w-5 shrink-0" aria-hidden="true" /><span>{{
							t("lead")
						}}</span>
					</div>
					<ProfileCollectionForm
						:profile="profile"
						:lang="lang"
						:submitting="saving"
						:error="saveError"
						@submit="submit"
					/>
					<button v-if="conflict" class="profile-secondary profile-reload" @click="load">
						{{ t("reload") }}
					</button>
				</section>
			</main>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ref } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { call, Icon } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"
import ProfileCollectionForm from "@/components/profile/ProfileCollectionForm.vue"
import { resolveHomeLanguage } from "@/utils/homeExperience"
import {
	PROFILE_COLLECTION_GET,
	PROFILE_COLLECTION_SAVE,
	profileCollectionCopy,
	profileSubmission,
} from "@/utils/profileCollection"

const lang = resolveHomeLanguage(window.frappe?.boot)
const t = (key) => profileCollectionCopy(key, lang)
const profile = ref(null)
const loading = ref(true)
const saving = ref(false)
const submitted = ref(false)
const unavailable = ref(false)
const loadError = ref("")
const saveError = ref("")
const conflict = ref(false)
const summaryFields = [
	"cell_number",
	"custom_wechat_id",
	"contact_email",
	"current_address",
	"person_to_be_contacted",
	"relation",
	"emergency_phone_number",
]

async function load() {
	loading.value = true
	profile.value = null
	submitted.value = false
	saveError.value = ""
	conflict.value = false
	unavailable.value = false
	try {
		profile.value = await call(PROFILE_COLLECTION_GET)
	} catch (error) {
		unavailable.value =
			error?.exc_type === "PermissionError" || error?.exc_type === "AuthenticationError"
		loadError.value = t(unavailable.value ? "unavailable" : "loadFailed")
	} finally {
		loading.value = false
	}
}

async function submit(values) {
	if (saving.value) return
	saving.value = true
	saveError.value = ""
	conflict.value = false
	try {
		profile.value = await call(PROFILE_COLLECTION_SAVE, {
			profile: profileSubmission(profile.value, values),
		})
		submitted.value = true
	} catch (error) {
		conflict.value = error?.exc_type === "TimestampMismatchError"
		saveError.value = t(
			conflict.value
				? "conflict"
				: error?.exc_type === "PermissionError"
				? "unavailable"
				: "saveFailed"
		)
	} finally {
		saving.value = false
	}
}

onIonViewWillEnter(load)
</script>

<style scoped>
.profile-collection-page {
	width: 100%;
	max-width: 580px;
	margin: 0 auto;
	padding: 10px 16px calc(28px + env(safe-area-inset-bottom, 0px));
}
.profile-state,
.profile-form-card,
.profile-success {
	padding: 22px 18px;
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 18px;
	background: var(--h-bg-elevated, #fff);
}
.profile-state {
	margin-top: 16px;
	text-align: center;
	line-height: 1.7;
	color: var(--h-fg-secondary, #64706a);
}
.profile-form-lead {
	display: flex;
	align-items: center;
	gap: 9px;
	margin-bottom: 20px;
	padding: 12px;
	border-radius: 10px;
	background: #eaf4ec;
	color: #245b43;
	font-size: 14px;
	line-height: 1.5;
}
.profile-success {
	padding-top: 30px;
	text-align: center;
}
.profile-success-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 94px;
	height: 94px;
	margin: 0 auto 20px;
	border: 12px solid #e7f3e9;
	border-radius: 50%;
	background: #23755b;
	color: #fff;
}
.profile-success h1 {
	margin: 0 0 12px;
	color: var(--h-fg-primary, #161b1a);
	font-size: 27px;
	font-weight: 700;
}
.profile-success-lead {
	color: var(--h-fg-secondary, #64706a);
	font-size: 15px;
	line-height: 1.8;
}
.profile-success-summary {
	margin: 24px 0;
	padding: 16px;
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 12px;
	text-align: left;
}
.profile-success-summary div {
	display: grid;
	grid-template-columns: 100px 1fr;
	gap: 12px;
	padding: 8px 0;
}
.profile-success-summary dt {
	font-size: 13px;
	line-height: 1.6;
	color: var(--h-fg-secondary, #64706a);
}
.profile-success-summary dd {
	margin: 0;
	font-size: 14px;
	line-height: 1.6;
	white-space: pre-wrap;
	overflow-wrap: anywhere;
	color: var(--h-fg-primary, #161b1a);
}
.profile-primary,
.profile-secondary {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 48px;
	padding: 12px 20px;
	border-radius: 10px;
	font-size: 16px;
	font-weight: 600;
	text-decoration: none;
}
.profile-primary {
	background: #23755b;
	color: #fff;
}
.profile-secondary {
	margin-top: 15px;
	border: 1px solid var(--h-bd-default, #e3dfd4);
	color: var(--h-fg-primary, #161b1a);
}
.profile-reload {
	width: 100%;
}
.profile-edit-again,
.profile-home-link {
	display: block;
	width: 100%;
	margin-top: 12px;
	min-height: 44px;
	padding: 12px;
	color: #23755b;
	font-size: 15px;
	text-align: center;
}
button:focus-visible,
a:focus-visible {
	outline: 2px solid #23755b;
	outline-offset: 3px;
}
</style>
